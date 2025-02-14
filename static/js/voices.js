// --------- Audio Recording & Upload ---------
let mediaRecorder;
let audioChunks = [];
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const recordingStatus = document.getElementById('recordingStatus');

// When the document is ready, fetch the list of voices
function fetchVoices() {
    fetch("/api/voices/get-info")
      .then((response) => response.json())
      .then((data) => {

        const voiceListDiv = document.getElementById("voiceList");
        const customVoiceListDiv = document.getElementById("customVoiceList");
        voiceListDiv.innerHTML = ""; // Clear current list
        customVoiceListDiv.innerHTML = ""; // Clear current list

        if (data.voices.length === 0) {

          voiceListDiv.innerHTML = "<div class='no-files'>No voice files available.</div>";

        } else {

          data.voices.forEach((file) => {

            // Create a card container
            const card = document.createElement("div");
            card.className = "mb-2";

            // Card header with the file name
            const header = document.createElement("div");
            header.className = "card-header";
            header.textContent = file.filename;

            // Audio container
            const audioContainer = document.createElement("div");
            audioContainer.className = "audio-container py-2";

            // Audio element
            const audio = document.createElement("audio");
            audio.className = "audio-player w-100";
            audio.controls = true;
            audio.src = `${file.filepath}`;

            // Assemble card
            audioContainer.appendChild(audio);
            card.appendChild(header);
            card.appendChild(audioContainer);
            voiceListDiv.appendChild(card);
          });
        }
        console.log(data.custom_voices);
        if (data.custom_voices.length === 0) {

            customVoiceListDiv.innerHTML = "<div class='no-files'>No custom voice files available.</div>";
  
        } else {

            data.custom_voices.forEach((file) => {

                // Create a card container
                const card = document.createElement("div");
                card.className = "mb-2";

                // Card header with the file name
                const header = document.createElement("div");
                header.className = "card-header";
                header.textContent = file.filename;

                // Audio container
                const audioContainer = document.createElement("div");
                audioContainer.className = "audio-container py-2";

                // Audio element
                const audio = document.createElement("audio");
                audio.className = "audio-player w-100";
                audio.controls = true;
                audio.src = `${file.filepath}`;

                // Assemble card
                audioContainer.appendChild(audio);
                card.appendChild(header);
                card.appendChild(audioContainer);
                customVoiceListDiv.appendChild(card);
            });
        }
      })
      .catch((error) => {
        console.error("Error fetching voices:", error);
      });
  }

  // Load voice files on page load
  document.addEventListener("DOMContentLoaded", fetchVoices);


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
            // Optionally, refresh the voice files list
            fetchVoices();
        })
        .catch(error => {
            console.error("Error uploading recording:", error);
            recordingStatus.textContent = "Error saving recording.";
        });
    });
});