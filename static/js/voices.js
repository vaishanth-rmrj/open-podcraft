

// fetch the list of voices
function fetchVoices() {
  fetch("/api/voices/get-info")
  .then(response => response.json())
  .then(data => {
      const voiceListDiv = document.getElementById("voiceList");
      const customVoiceListDiv = document.getElementById("customVoiceList");

      voiceListDiv.innerHTML = ""; // Clear current list
      customVoiceListDiv.innerHTML = ""; // Clear current list

      function renderVoiceList(container, voices, noFilesText) {
          if (voices.length === 0) {
              container.innerHTML = `<div class='no-files'>${noFilesText}</div>`;
          } else {
              voices.forEach(file => {
                  const newContent = `
                      <div class="mb-2">
                          <div class="card-header">${file.filename}</div>
                          <div class="audio-container py-2">
                              <audio class="audio-player w-100" controls src="${file.filepath}"></audio>
                          </div>
                      </div>
                  `;
                  container.insertAdjacentHTML("beforeend", newContent);
              });
          }
      }

      renderVoiceList(voiceListDiv, data.voices, "No voice files available.");
      renderVoiceList(customVoiceListDiv, data.custom_voices, "No custom voice files available.");
  })
  .catch(error => {
      console.error("Error fetching voices:", error);
  });
}
// Load voice files on page load
document.addEventListener("DOMContentLoaded", fetchVoices);

// --------- Audio Recording & Upload ---------
let mediaRecorder;
let audioChunks = [];
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const recordingStatus = document.getElementById('recordingStatus');

startBtn.addEventListener('click', async () => {
  // Request access to microphone
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.start();
    recordingStatus.textContent = "Recording...";
    startBtn.disabled = true;
    stopBtn.disabled = false;

    // Clear previous recordings
    audioChunks = [];

    mediaRecorder.addEventListener("dataavailable", event => {
      audioChunks.push(event.data);
    });
  } catch (err) {
    console.error("Error accessing microphone:", err);
    recordingStatus.textContent = "Microphone access denied.";
  }
});

// When the stop button is clicked
stopBtn.addEventListener('click', () => {
  mediaRecorder.stop();
  recordingStatus.textContent = "Processing recording...";
  startBtn.disabled = false;
  stopBtn.disabled = true;

  mediaRecorder.addEventListener("stop", () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      // Prepare form data to send file to the backend
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.wav');

      // Get the entered voice name from the input field
      const voiceNameInput = document.getElementById('voiceName');
      const voiceName = voiceNameInput ? voiceNameInput.value : "unnamed_voice";
      formData.append('voiceName', voiceName);

      fetch('/api/voices/upload', {
          method: 'POST',
          body: formData
      })
      .then(response => response.json())
      .then(data => {
          recordingStatus.textContent = "Recording saved!";          
          fetchVoices(); // refresh the voice files list
      })
      .catch(error => {
          console.error("Error uploading recording:", error);
          recordingStatus.textContent = "Error saving recording.";
      });
  });
});