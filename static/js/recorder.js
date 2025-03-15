// static/js/recorder.js
class AudioRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.stream = null;
    }

    // 开始录音
    async startRecording() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(this.stream);
            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                this.audioChunks.push(event.data);
            };

            this.mediaRecorder.onstop = () => {
                const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                this.onRecordingComplete(audioBlob);
            };

            this.mediaRecorder.start();
            console.log("Recording started");
            return true;
        } catch (error) {
            console.error("Error starting recording:", error);
            alert("无法访问麦克风，请检查权限");
            return false;
        }
    }

    // 停止录音
    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
            this.mediaRecorder.stop();
            this.stream.getTracks().forEach(track => track.stop());
            console.log("Recording stopped");
        }
    }

    // 录音完成回调
    setOnRecordingComplete(callback) {
        this.onRecordingComplete = callback;
    }
}

// 导出单例实例
const recorder = new AudioRecorder();
export default recorder;
