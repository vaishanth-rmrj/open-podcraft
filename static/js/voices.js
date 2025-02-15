

// fetch the list of voices
function fetchVoices() {
  fetch("/api/voices/get-info")
  .then(response => response.json())
  .then(data => {
      const voiceListDiv = document.getElementById("voiceList");
      const customVoiceListDiv = document.getElementById("customVoiceList");

      function renderVoiceList(container, voices, noFilesText) {
          if (voices.length === 0) {
              container.innerHTML = `<h6 class="text-secondary">Clone your voice to get started!</h6>`;
          } else {
                container.innerHTML = "";
              voices.forEach(file => {
                  const newContent = `
                      <div class="mb-2">
                          <div class="card-header mb-2">
                            <strong>${file.filename}</strong>
                          </div>
                          <div class="audio-container py-2">
                              <audio class="w-100" controls src="${file.filepath}"></audio>
                          </div>
                      </div>
                  `;
                  container.insertAdjacentHTML("beforeend", newContent);
              });
          }
      }

      // Function to render custom voices (with delete button)
      function renderCustomVoiceList(container, voices) {
        if (voices.length === 0) {
          container.innerHTML = `<h6 class="text-secondary">Clone your voice to get started!</h6>`;
        } else {
          container.innerHTML = "";
          voices.forEach((file) => {
            // Use a unique id (e.g., using the filename) to help remove the element later.
            const newContent = `
              <div class="mb-2" id="voice-${file.filename}">
                <div class="card-header mb-2 d-flex justify-content-between align-items-center">
                  <strong>${file.filename}</strong>
                  <button class="btn btn-danger btn-sm delete-btn" data-filename="${file.filename}">
                    Delete
                  </button>
                </div>
                <div class="audio-container py-2">
                  <audio class="w-100" controls src="${file.filepath}"></audio>
                </div>
              </div>
            `;
            container.insertAdjacentHTML("beforeend", newContent);
          });
        }
      }

      renderVoiceList(voiceListDiv, data.voices, "No voice files available.");
      renderCustomVoiceList(customVoiceListDiv, data.custom_voices);
  })
  .catch(error => {
      console.error("Error fetching voices:", error);
  });
}
// fetch the list of voices
function fetchVoices() {
  fetch("/api/voices/get-info")
    .then((response) => response.json())
    .then((data) => {
      const voiceListDiv = document.getElementById("voiceList");
      const customVoiceListDiv = document.getElementById("customVoiceList");

      // Function to render normal voices (without delete button)
      function renderVoiceList(container, voices, noFilesText) {
        if (voices.length === 0) {
          container.innerHTML = `<h6 class="text-secondary">${noFilesText}</h6>`;
        } else {
          container.innerHTML = "";
          voices.forEach((file) => {
            const newContent = `
              <div class="mb-2">
                  <div class="card-header mb-2">
                    <strong>${file.filename}</strong>
                  </div>
                  <div class="audio-container py-2">
                      <audio class="w-100" controls src="${file.filepath}"></audio>
                  </div>
              </div>
            `;
            container.insertAdjacentHTML("beforeend", newContent);
          });
        }
      }

      // Function to render custom voices (with delete button)
      function renderCustomVoiceList(container, voices) {
        if (voices.length === 0) {
          container.innerHTML = `<h6 class="text-secondary">Clone your voice to get started!</h6>`;
        } else {
          container.innerHTML = "";
          voices.forEach((file) => {
            // Use a unique id (e.g., using the filename) to help remove the element later.
            const newContent = `
              <div class="mb-2" id="voice-${file.filename}">
                <div class="card-header mb-2 d-flex justify-content-between align-items-center">
                  <strong>${file.filename}</strong>
                  <button class="btn btn-outline-danger btn-sm p-2 delete-btn" data-filepath="${file.filepath}">
                    Delete
                  </button>
                </div>
                <div class="audio-container py-2">
                  <audio class="w-100" controls src="${file.filepath}"></audio>
                </div>
              </div>
            `;
            container.insertAdjacentHTML("beforeend", newContent);
          });
        }
      }

      renderVoiceList(voiceListDiv, data.voices, "No voice files available.");
      renderCustomVoiceList(customVoiceListDiv, data.custom_voices);
    })
    .catch((error) => {
      console.error("Error fetching voices:", error);
    });
}

// Attach an event listener to the custom voices container to handle delete clicks.
document.addEventListener("DOMContentLoaded", () => {
  fetchVoices();

  const customVoiceListDiv = document.getElementById("customVoiceList");

  // Event delegation: listen for clicks on any delete button within the custom voice list
  customVoiceListDiv.addEventListener("click", (event) => {
    if (event.target.classList.contains("delete-btn")) {
      const filepath = event.target.getAttribute("data-filepath");
      if (confirm(`Are you sure you want to delete "${filepath}"?`)) {
        // Call the backend delete endpoint
        fetch("/api/voices/delete", {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ filepath }),
        })
          .then((response) => {
            if (response.ok) {
              // Remove the voice element from the UI
              const voiceElement = document.getElementById(`voice-${filepath}`);
              if (voiceElement) {
                voiceElement.remove();
              }
            } else {
              response.json().then((data) => {
                alert(`Error: ${data.detail || "Failed to delete voice."}`);
              });
            }
          })
          .catch((error) => {
            console.error("Error deleting voice:", error);
          });
      }
    }
  });
});


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