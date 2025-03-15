import whisper
from pydub import AudioSegment
import io
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局加载 Whisper 模型（只加载一次）
MODEL = whisper.load_model("base")  # 可根据需求改为 "small", "medium", "large"
# 显式指定 ffmpeg 和 ffprobe 路径（根据实际安装路径调整）
AudioSegment.ffmpeg = "D:\\ffmpeg-7.0.2-essentials_build\\bin\\ffmpeg.exe"
AudioSegment.ffprobe = "D:\\ffmpeg-7.0.2-essentials_build\\bin\\ffprobe.exe"


def recognize_speech(audio_file):
    """
    将音频文件转为文本。
    参数：
        audio_file: Werkzeug FileStorage 对象（上传的音频文件）
    返回：
        str: 识别出的文本，或 None（如果失败）
    """
    temp_webm = "temp_audio.webm"
    temp_wav = "temp_audio.wav"

    try:
        # 保存上传的音频文件
        logger.info(f"Processing audio file: {audio_file.filename}")
        audio_file.save(temp_webm)

        # 将 webm 转为 wav
        logger.debug("Converting webm to wav")
        audio = AudioSegment.from_file(temp_webm, format="webm")
        audio.export(temp_wav, format="wav")

        # 使用 Whisper 进行语音识别
        logger.debug("Transcribing audio with Whisper")
        result = MODEL.transcribe(temp_wav, language="en")  # 指定语言，例如 "zh"（中文）或 "en"（英文）
        recognized_text = result['text'].strip()
        logger.info(f"Recognized text: {recognized_text}")
        return recognized_text

    except FileNotFoundError as e:
        logger.error(f"FFmpeg not found: {e}. Please install ffmpeg and add it to PATH.")
        return None
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return None
    finally:
        # 清理临时文件
        for temp_file in [temp_webm, temp_wav]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to remove temp file {temp_file}: {e}")


if __name__ == "__main__":
    # 测试代码
    from werkzeug.datastructures import FileStorage

    with open("test_audio.webm", "rb") as f:
        audio_file = FileStorage(f, filename="test_audio.webm")
        result = recognize_speech(audio_file)
        print(f"Recognized text: {result}")
