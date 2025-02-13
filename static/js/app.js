


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


    };

    flagsCheckEventSource.onerror = function(error) {
        console.error("Error with EventSource:", error);
        flagsCheckEventSource.close();
    };
}
checkPodcastScriptStatus();