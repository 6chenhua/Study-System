document.getElementById("quizForm").addEventListener("submit", function(e) {
    e.preventDefault();
    const userId = this.dataset.userId;
    const day = this.dataset.day;
    let answers = {};
    new FormData(this).forEach((value, key) => {
        answers[key] = value;
    });
    console.log("Submitting answers:", answers);

    fetch(`/quiz/${userId}/${day}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Server response:", data);
        if (data.next === "video") {
            // 如果有 return_day 参数，附加到 URL 中
            const videoUrl = data.return_day
                ? `/video/${data.user_id}/${data.day}?return_day=${data.return_day}`
                : `/video/${data.user_id}/${data.day}`;
            window.location.href = videoUrl;
        } else if (data.next === "practice") {
            window.location.href = `/practice/${data.user_id}/${data.day}`;
        } else if (data.next === "quiz") {
            window.location.href = `/quiz/${data.user_id}/${data.day}`;
        } else if (data.next === "rest") {
            window.location.href = `/rest/${data.user_id}/${data.day}`;
        } else if (data.next === "done") {
            window.location.href = `/done/${data.user_id}`;
        } else {
            console.error("Unknown next value:", data.next);
            window.location.href = `/video/${data.user_id}/${data.day}`;
        }
    })
    .catch(error => console.error("Error:", error));
});
