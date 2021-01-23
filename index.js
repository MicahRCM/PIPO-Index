let lastid = ""

const showDrop = (id) => {
    let ids = [`dataDrop`, `toolDrop`, `researchDrop`, `aboutDrop`]
    ids.forEach((n) => {
        document.getElementById(n).className = "dropContent"
        document.getElementById(n + "_1").className = "navbarItemContainer"
    })
    let element = document.getElementById(id)
    if (!element.selected) {
        element.className = "dropContent showDrop"
        document.getElementById(id + "_1").className = "navbarItemContainer navSelected"
        document.getElementById(`headerDrop`).className = "headerDrop showDrop"
    } else {
    	document.getElementById(id + "_1").className = "navbarItemContainer"	
    	document.getElementById(`headerDrop`).className = "headerDrop"
    }
    lastid = id
    element.selected = !element.selected
}

window.addEventListener('mousedown', e => {
    if (event.target.matches('.makeOpaque')) {
    	showDrop(lastid)
    }
});