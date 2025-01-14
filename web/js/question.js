function ShowAnswer(player) {
    let button = document.getElementById("show-btn")
    let answer = document.getElementById("answer")
    answer.classList.remove("hidden")
    button.remove()

    let audio = document.getElementById("audio")
    let timecode = audio.getAttribute("data-answer-timecode")
    let seek = audio.getAttribute("data-answer-seek")
    player.ParseTimecode(timecode)

    if (seek !== "")
        player.Seek(+seek)
}

function MakeFullTrack(player) {
    let block = document.getElementById("full-track")
    block.remove()

    player.ResetTimecode()
}

function CheckAnswer(isCorrect) {
    let questionType = document.getElementById("question").getAttribute("data-question-type")
    let link = document.getElementById("audio").getAttribute("data-link")

    let error = document.getElementById("check-answer-error")
    error.innerText = ""

    SendRequest("/add-statistic", {question_type: questionType, link: link, correct: isCorrect}).then(response => {
        if (response.status != "success") {
            error.innerText = response.message
            return
        }

        let block = document.getElementById("check-answer")
        block.remove()
        window.location = "/question"
    })
}

function AddToIgnore(artistIds) {
    let error = document.getElementById("ignore-error")
    error.innerText = ""

    let fetches = []

    for (let artistId of artistIds) {
        fetches.push(SendRequest("/artist-to-questions", {artist_id: artistId, list_name: "ignore"}).then(response => {
            if (response.status != "success") {
                error.innerText = response.message
                return false
            }

            return true
        }))
    }

    Promise.all(fetches).then(results => {
        for (result of results)
            if (!result)
                return

        let button = document.getElementById("ignore-btn")
        button.remove()
    })
}
