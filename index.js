const showDrop = (id) => {
	let ids = [`dataDrop`, `toolDrop`, `researchDrop`, `aboutDrop`]
	ids.forEach((n) => {
		document.getElementById(n).className = "dropContent"
		document.getElementById(n + "_1").className = "navbarItemContainer"
	})
	document.getElementById(id).className = "dropContent showDrop"
	document.getElementById(id + "_1").className = "navbarItemContainer navSelected"
}