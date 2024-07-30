import json
from datetime import datetime, timedelta
import librosa
import soundfile as sf
import os
from MessageUpdateHandler import MessageUpdateHandler
from FileUploadHandler import FileUploadHandler

PROCESSED_MEDIA_DIR = "./processed_media"


def clean_audio_timestamps(audio_timestamps):
    cleaned_timestamps = {}
    for entry in audio_timestamps:
        start = entry['start']
        if start not in cleaned_timestamps:
            cleaned_timestamps[start] = entry
        else:
            if entry['is_final']:
                cleaned_timestamps[start] = entry
            elif not cleaned_timestamps[start]['is_final']:
                cleaned_timestamps[start] = entry
    return list(cleaned_timestamps.values())


def map_to_absolute_timestamps(audio_timestamps, audio_started_at, audio_pause_timestamps):
    audio_started_at = datetime.fromtimestamp(audio_started_at / 1000.0)  # Convert to datetime object
    pause_durations = [end - start for start, end in audio_pause_timestamps]
    pause_offsets = [sum(pause_durations[:i]) for i in range(len(pause_durations) + 1)]
    pause_intervals = [(start, end) for start, end in audio_pause_timestamps]

    absolute_timestamps = []
    for entry in audio_timestamps:
        relative_start = entry['start'] * 1000  # Convert seconds to milliseconds
        offset = sum(pause_offsets[i] for i, (pause_start, pause_end) in enumerate(pause_intervals) if
                     relative_start >= (pause_start - audio_started_at.timestamp() * 1000))
        absolute_start = audio_started_at + timedelta(milliseconds=relative_start + offset)
        entry['absolute_start'] = absolute_start
        absolute_timestamps.append(entry)

    return absolute_timestamps


def organize_transcriptions_by_message(absolute_timestamps, user_msg_timestamps):
    sorted_msgs = sorted(user_msg_timestamps.items(), key=lambda x: int(x[0]))
    result = []

    for i, (timestamp, msg_id) in enumerate(sorted_msgs):
        if i == 0:
            prev_timestamp = 0
        else:
            prev_timestamp = int(sorted_msgs[i - 1][0])

        current_timestamp = int(timestamp)
        transcriptions = [entry for entry in absolute_timestamps if
                          prev_timestamp <= entry['timestamp'] < current_timestamp]

        result.append({"msg_id": msg_id, "transcriptions": transcriptions})

    last_msg_id = sorted_msgs[-1][1]
    last_timestamp = int(sorted_msgs[-1][0])
    # if last msg id is the same as the last msg in the result, update the last entry's transcriptions
    remaining_transcriptions = [entry for entry in absolute_timestamps if entry['timestamp'] >= last_timestamp]
    if remaining_transcriptions:
        if result and result[-1]['msg_id'] == last_msg_id:
            result[-1]['transcriptions'].extend(remaining_transcriptions)
        else:
            result.append({"msg_id": last_msg_id,
                           "transcriptions": remaining_transcriptions})
    return result


def process_for_audio(organized_transcriptions):
    final_result = {}

    for item in organized_transcriptions:
        msg_id = item["msg_id"]
        transcriptions = item["transcriptions"]

        if not transcriptions:
            continue

        relative_start = min(transcription['start'] for transcription in transcriptions)
        relative_end = max(transcription['start'] + transcription['duration'] for transcription in transcriptions)

        metadata = []
        for transcription in transcriptions:
            metadata.append({
                "text": transcription['text'],
                "relative_start": transcription['start'],
                "abs_start": transcription['absolute_start'],
                "duration": transcription['duration']
            })

        final_result[msg_id] = {
            "relative_start": relative_start,
            "relative_end": relative_end,
            "metadata": metadata
        }

    return final_result


def load_wav_file(file_path):
    data, rate = librosa.load(file_path, sr=None)
    return rate, data


def write_audio_file(file_path, data, rate):
    sf.write(file_path, data, rate)


def cut_audio_segments(rate, data, final_result):
    thread_id = final_result.pop('thread_id')
    ws_conn_sid = final_result.pop('ws_conn_sid')
    message_update_handler = MessageUpdateHandler()
    file_upload_handler = FileUploadHandler()
    for msg_id, info in final_result.items():
        start_sample = int(info['relative_start'] * rate)
        end_sample = int(info['relative_end'] * rate)
        segment_data = data[start_sample:end_sample]

        # replace # in msg_id with _ to avoid path issues
        msg_id_for_file = msg_id.replace("#", "_")
        # save file to ./processed_media/{thread_id}/{ws_conn_sid}/{msg_id}.mp3
        file_name = f"{PROCESSED_MEDIA_DIR}/{thread_id}/{ws_conn_sid}/{msg_id_for_file}.mp3"
        # create directories if they don't exist
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        write_audio_file(file_name, segment_data, rate)
        # update the message in DynamoDB to set has_audio to True
        message_update_handler.update_message_audio_flag(thread_id, msg_id[-13:])
        # upload the file to S3
        file_upload_handler.upload_file(file_name, f"{thread_id}/", is_public=True)
        print(f"Exported {file_name}")


def datetime_converter(o):
    if isinstance(o, datetime):
        return o.isoformat()
    return o


def process_recording_metadata(metadata_file_path) -> dict | bool:
    with open(metadata_file_path, 'r') as file:
        metadata = json.load(file)

    audio_timestamps = metadata['audio_timestamps']
    audio_started_at = metadata['audio_started_at']
    audio_pause_timestamps = metadata['audio_pause_timestamps']
    user_msg_timestamps = metadata['user_msg_timestamps']
    thread_id = metadata['thread_id']
    ws_conn_sid = metadata['ws_conn_sid']

    if not user_msg_timestamps:
        print(
            f"No user messages found in metadata, skipping processing, thread_id: {thread_id}, ws_conn_sid: {ws_conn_sid}")
        return False

    if not audio_timestamps:
        print(
            f"No audio transcription timestamps found in metadata, skipping processing, thread_id: {thread_id}, ws_conn_sid: {ws_conn_sid}")
        return False

    cleaned_timestamps = clean_audio_timestamps(audio_timestamps)
    absolute_timestamps = map_to_absolute_timestamps(cleaned_timestamps, audio_started_at, audio_pause_timestamps)
    organized_transcriptions = organize_transcriptions_by_message(absolute_timestamps, user_msg_timestamps)
    final_result = process_for_audio(organized_transcriptions)
    final_result['thread_id'] = thread_id
    final_result['ws_conn_sid'] = ws_conn_sid

    # save final_result to json file in ./processed_media/{thread_id}/{ws_conn_sid}/thread_id[0:8]_ws_conn_sid_processed.json
    file_name = f"{PROCESSED_MEDIA_DIR}/{thread_id}/{ws_conn_sid}/{thread_id[0:8]}_{ws_conn_sid}_processed.json"
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with open(file_name, 'w') as file:
        json.dump(final_result, file, indent=2, default=datetime_converter)
    file_upload_handler = FileUploadHandler()
    file_upload_handler.upload_file(file_name, f"{thread_id}/")
    return final_result


def process_audio_file(wav_file_path, final_result):
    rate, data = load_wav_file(wav_file_path)
    cut_audio_segments(rate, data, final_result)
