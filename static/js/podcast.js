
document.getElementById('generatePodcastScriptBtn')
.addEventListener('click', async (event) => {
  event.preventDefault();

  const chaptersForm = document.getElementById('podcastChaptersForm');
  const formData = new FormData(chaptersForm);
  const response = await fetch(chaptersForm.action, {
      method: chaptersForm.method,
      body: formData
  });

  if (response.ok) {
      alert('Generating podcast script');
  } else {
      alert('Error generating podcast script!!');
  }
});

async function populatePodcastScript(){
  const container = document.getElementById("podcastLinesDisplay");

  try {

      const response = await fetch("/api/podcasts/get-script");
      const dataList = await response.json();

      container.innerHTML = "";
      dataList.forEach(data => {
        const newContent = `
            <div class="d-flex">
              <div style="min-width:100px">
                <strong>${data.speaker}</strong>
              </div>

              <div>
                <p>${data.content}</p>
              </div>
            </div>
            
        `;
        container.insertAdjacentHTML("beforeend", newContent);
    });
  } catch (error) {
      console.error("Error getting script lines", error);
  }
};

function checkPodcastScriptStatus() {

  const flagsCheckEventSource = new EventSource('/api/check_flags');
  flagsCheckEventSource.onmessage = function(event) {
      const data = JSON.parse(event.data);
      console.log(data);
      

      const spinnerDisplay = document.getElementById("podcatScriptGenSpinner");
      const notFoundMsgDisplay = document.getElementById("notFoundMsgDisplay");
      const scriptLinesDisplay = document.getElementById("podcastLinesDisplay");

      if (data.is_generating_script) {
          
          spinnerDisplay.classList.remove("d-none");
          notFoundMsgDisplay.classList.add("d-none");
          scriptLinesDisplay.classList.add("d-none");

      } 
      if (!data.is_generating_script && !data.is_script_available){

          spinnerDisplay.classList.add("d-none");
          notFoundMsgDisplay.classList.remove("d-none");
          scriptLinesDisplay.classList.add("d-none");

      } 
      if (data.is_script_available) {
          console.log(data.is_script_available);
          spinnerDisplay.classList.add("d-none");
          notFoundMsgDisplay.classList.add("d-none");
          scriptLinesDisplay.classList.remove("d-none");
          populatePodcastScript();
      }    
      
      if (data.is_generating_podcast) {            
          showGeneratingAnimationPodcastAudio();
      }     

      if (data.is_podcast_available) {
          const podcastAudioPlayerProgressBar = document.getElementById("podcastAudioPlayerProgressBar");
          podcastAudioPlayerProgressBar.classList.add("d-none");
          fetchAndUpdateAudioUrl();
      }
  };

  flagsCheckEventSource.onerror = function(error) {
      console.error("Error with EventSource:", error);
      flagsCheckEventSource.close();
  };
}
checkPodcastScriptStatus();

// const saveTranscriptBtn = document.getElementById("saveTranscriptBtn");
// saveTranscriptBtn.addEventListener("click", () => {
//     const podcastUuid = saveTranscriptBtn.getAttribute("data-uuid");

//     // Send the UUID as a plain text payload using fetch
//     fetch("/api/podcasts/save-transcript", {
//         method: "POST",
//         headers: {
//             "Content-Type": "text/plain"
//         },
//         body: podcastUuid
//     })
//     .then(response => {
//         if (!response.ok) {
//         throw new Error("Network response was not ok: " + response.statusText);
//         }
//         return response.json();
//     })
//     .then(data => {
//         console.log("Success:", data);
//         alert("Transcript updated successfully!");
//     })
//     .catch(error => {
//         console.error("Error:", error);
//         alert("Error updating transcript.");
//     });
// });

const generatePodcastBtn = document.getElementById("generatePodcastBtn");
generatePodcastBtn.addEventListener("click", () => {
    const podcastUuid = generatePodcastBtn.getAttribute("data-uuid");

    // Send the UUID as a plain text payload using fetch
    fetch("/api/podcasts/generate-podcast", {
        method: "POST",
        headers: {
            "Content-Type": "text/plain"
        },
        body: podcastUuid
    })
    .then(response => {
        if (!response.ok) {
        throw new Error("Network response was not ok: " + response.statusText);
        }
        return response.json();
    })
    .then(data => {
        console.log("Success:", data);
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Error generating podcast.");
    });
});


document.addEventListener("DOMContentLoaded", function() {
    const audio = document.getElementById("audioPlayer");
    const playPauseBtn = document.getElementById("playPauseBtn");
    const rewindBtn = document.getElementById("rewindBtn");
    const forwardBtn = document.getElementById("forwardBtn");
    const progressBar = document.querySelector(".audio-player-progress");
    const currentTimeEl = document.getElementById("currentTime");
    const durationEl = document.getElementById("duration");

    // Format seconds to MM:SS
    function formatTime(seconds) {
      const minutes = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      return `${minutes}:${secs < 10 ? "0" : ""}${secs}`;
    }

    // Update progress bar and time info
    function updateProgress() {
      const current = audio.currentTime;
      const duration = audio.duration;
      if (duration) {
        const percent = (current / duration) * 100;
        progressBar.style.width = percent + "%";
        currentTimeEl.textContent = formatTime(current);
        durationEl.textContent = formatTime(duration);
      }
    }

    // Toggle play/pause
    playPauseBtn.addEventListener("click", function() {
      if (audio.paused) {
        audio.play();
        playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
      } else {
        audio.pause();
        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
      }
    });

    // Rewind 10 seconds
    rewindBtn.addEventListener("click", function() {
      audio.currentTime = Math.max(0, audio.currentTime - 10);
    });

    // Fast-forward 10 seconds
    forwardBtn.addEventListener("click", function() {
      audio.currentTime = Math.min(audio.duration, audio.currentTime + 10);
    });

    // Update progress as the audio plays
    audio.addEventListener("timeupdate", updateProgress);

    // Update duration once metadata is loaded
    audio.addEventListener("loadedmetadata", () => {
      durationEl.textContent = formatTime(audio.duration);
    });

    // Optionally, update the button icon when the audio ends
    audio.addEventListener("ended", () => {
      playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
    });
  });

function fetchAndUpdateAudioUrl() {
  // Get references to the UI elements
  const playPauseBtn = document.getElementById("playPauseBtn");
  const rewindBtn = document.getElementById("rewindBtn");
  const forwardBtn = document.getElementById("forwardBtn");
  const progressContainer = document.getElementById("progressContainer");
  const stopBtn = document.getElementById("stopBtn");
  const audioPlayer = document.getElementById("audioPlayer");

  // Send a GET request to fetch the audio URL.
  fetch("/api/podcasts/get-audio-url")
    .then(response => {
      if (!response.ok) {
        throw new Error("Failed to fetch audio URL");
      }

      return response.json();
    })
    .then(data => {
      const audioUrl = data.audio_url;
      if (audioUrl) {
        
        // Update the audio element's source and load the new URL
        audioPlayer.src = audioUrl;
        audioPlayer.load();

        stopBtn.style.display = "none";
        playPauseBtn.style.display = "inline-block";
        rewindBtn.style.display = "inline-block";
        forwardBtn.style.display = "inline-block";
        progressContainer.style.display = "block";

      } else {
        console.error("No audio URL found in response");

      }
    })
    .catch(error => {
      console.error("Error fetching audio URL:", error);

    });
}

function showGeneratingAnimationPodcastAudio() {

  const playPauseBtn = document.getElementById("playPauseBtn");
  const rewindBtn = document.getElementById("rewindBtn");
  const forwardBtn = document.getElementById("forwardBtn");
  const progressContainer = document.getElementById("progressContainer");
  const stopBtn = document.getElementById("stopBtn");
  const podcastAudioPlayerProgressBar = document.getElementById("podcastAudioPlayerProgressBar");
  
  podcastAudioPlayerProgressBar.classList.remove("d-none");
  stopBtn.style.display = "inline-block";
  playPauseBtn.style.display = "none";
  rewindBtn.style.display = "none";
  forwardBtn.style.display = "none";
  progressContainer.style.display = "none";
}

document.addEventListener("DOMContentLoaded", function () {
  // Fetch voice data from the backend.
  fetch("/api/voices/get-info")
    .then((response) => response.json())
    .then((data) => {
      const voiceSelect = document.getElementById("voiceSelect");
      // Clear the select (keep the default placeholder)
      voiceSelect.innerHTML = '<option value="" selected>Choose a voice</option>';

      // A helper function to add an option.
      function addOption(voice) {
        // If voice is an object, use its "name" property, else assume it's a string.
        const voiceName = typeof voice === "object" ? voice.filename : voice;
        const option = document.createElement("option");
        option.value = voiceName;
        option.textContent = voiceName;
        voiceSelect.appendChild(option);
      }

      // Populate the voices from both lists.
      if (data.voices && Array.isArray(data.voices)) {
        data.voices.forEach(addOption);
      }
      if (data.custom_voices && Array.isArray(data.custom_voices)) {
        data.custom_voices.forEach(addOption);
      }
    })
    .catch((error) => {
      console.error("Error fetching voices:", error);
    });
});


let currentSpeakerID = "";

// When the modal is about to be shown, update its title and record which speaker is being updated.
const voiceModal = document.getElementById("voiceModal");
voiceModal.addEventListener("show.bs.modal", function (event) {
  const button = event.relatedTarget;
  currentSpeakerID = button.getAttribute("data-speaker-id");

  // Update modal title for the selected speaker.
  const modalTitle = voiceModal.querySelector(".modal-title");
  modalTitle.textContent = "Select Voice for Speaker" + currentSpeakerID;
  
  // Reset the select field (optional)
  document.getElementById("voiceSelect").selectedIndex = 0;
});

    // When the save button is clicked in the modal...
document.getElementById("saveVoiceBtn").addEventListener("click", function () {
  const selectedVoice = document.getElementById("voiceSelect").value;
  if (selectedVoice) {
    // Update the corresponding speaker's display area with the selected voice.
    document.getElementById("speaker"+currentSpeakerID + "VoiceDisplay").innerHTML =
      "Voice: " + selectedVoice;
    
    // Get podcast uuid from the hidden input field.
    const saveVoiceBtn = document.getElementById("saveVoiceBtn");
    const podcastUuid = saveVoiceBtn.dataset.uuid;
    
    // Create the payload to send.
    const payload = {
      podcast_uuid: podcastUuid,
      speaker_id: currentSpeakerID,
      voice_name: selectedVoice,
    };

    // Send the POST request to the FastAPI backend.
    fetch("/api/voices/set", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
      .then(response => response.json())
      .then(data => {
        console.log("Response from backend:", data);
      })
      .catch(error => {
        console.error("Error sending voice data:", error);
      });
  }
  // Hide the modal.
  const modalInstance = bootstrap.Modal.getInstance(voiceModal);
  modalInstance.hide();
});
  