$(function(){
  $("#nav-placeholder").load("../toolbar.html");
});

const genEntries = () => {
	for (let i = 0; i < ENTRIES.length; i++) {
		let container = document.createElement(`div`)
		container.classList.add("entry_container")

	}
}