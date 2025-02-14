


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

        const response = await fetch("/api/get_podcast_script");
        const dataList = await response.json();

        container.innerHTML = "";
        // populate the container with cards
        dataList.forEach(data => {

            const row = document.createElement("div");
            row.className = "row";

            const speakerNameCol = document.createElement("div");
            speakerNameCol.className = "col-2";

            const speakerName = document.createElement("strong");
            speakerName.textContent = data.speaker;
            speakerNameCol.appendChild(speakerName);
            
            const speakerTextCol = document.createElement("div");
            speakerTextCol.className = "col-10";

            const speakerText = document.createElement("p");
            speakerText.textContent = data.content;
            speakerTextCol.appendChild(speakerText);

            row.append(speakerNameCol);
            row.append(speakerTextCol);
            container.appendChild(row);
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

const saveTranscriptBtn = document.getElementById("saveTranscriptBtn");
saveTranscriptBtn.addEventListener("click", () => {
    const podcastUuid = saveTranscriptBtn.getAttribute("data-uuid");

    // Send the UUID as a plain text payload using fetch
    fetch("/api/podcasts/save-transcript", {
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
        alert("Transcript updated successfully!");
    })
    .catch(error => {
        console.error("Error:", error);
        alert("Error updating transcript.");
    });
});

const generatePodcastBtn = document.getElementById("generatePodcastBtn");
generatePodcastBtn.addEventListener("click", () => {
    const podcastUuid = generatePodcastBtn.getAttribute("data-uuid");

    // Send the UUID as a plain text payload using fetch
    fetch("/api/generate_podcast", {
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
        alert("Podcast generate successfully!");
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
  
    // The UI is already in the initial "stopped" state:
    //   - Controls (play, rewind, forward, progress) are hidden.
    //   - Stop button is visible.
  
    // Send a GET request to fetch the audio URL.
    fetch("/api/get_podcast_audio_url")
      .then(response => {
        if (!response.ok) {
          throw new Error("Failed to fetch audio URL");
        }
        return response.json();
      })
      .then(data => {
        // Assume the API returns a JSON object with an "audio_url" property.
        const audioUrl = data.audio_url;
        if (audioUrl) {
          // Update the audio element's source and load the new URL
          audioPlayer.src = audioUrl;
          audioPlayer.load();
  
          // Revert UI to normal audio player view:
          // Hide the red stop button and show all controls.
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
        // Optionally, you can keep the red stop button visible or show an error message.
      });
  }

  function showGeneratingAnimationPodcastAudio() {
    // Get references to the UI elements
    const playPauseBtn = document.getElementById("playPauseBtn");
    const rewindBtn = document.getElementById("rewindBtn");
    const forwardBtn = document.getElementById("forwardBtn");
    const progressContainer = document.getElementById("progressContainer");
    const stopBtn = document.getElementById("stopBtn");
    const audioPlayer = document.getElementById("audioPlayer");
    const podcastAudioPlayerProgressBar = document.getElementById("podcastAudioPlayerProgressBar");
    
    podcastAudioPlayerProgressBar.classList.remove("d-none");
    stopBtn.style.display = "inline-block";
    playPauseBtn.style.display = "none";
    rewindBtn.style.display = "none";
    forwardBtn.style.display = "none";
    progressContainer.style.display = "none";
  }
  
  