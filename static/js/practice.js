document.getElementById("practiceForm").addEventListener("submit", function(e) {
    e.preventDefault();
    const userId = this.dataset.userId;
    const day = this.dataset.day;
    let answers = {};
    new FormData(this).forEach((value, key) => answers[key] = value);

    fetch(`/practice/${userId}/${day}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Next action:", data.next, ". pra.js");
        if (data.next === "practice") {
            window.location.reload();
        } else if (data.next === "quiz") {
            window.location.href = `/quiz/${data.user_id}/${data.day}`;
        } else if (data.next === "video") {
            window.location.href = `/video/${data.user_id}/${data.day}`;
        } else if (data.next === "rest") {
            window.location.href = `/rest/${data.user_id}/${data.day}`;
        } else if (data.next === "done") {
            window.location.href = `/done/${data.user_id}`;
        } else if (data.next === "encourage") {
            window.location.href = `/encourage/${data.user_id}/${data.day}`;
        } else {
            console.error("Unknown next value:", data.next);
            window.location.href = `/video/${data.user_id}/${data.day}`;
        }
    })
    .catch(error => console.error("Error:", error));
});
