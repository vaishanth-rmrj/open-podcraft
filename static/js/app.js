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