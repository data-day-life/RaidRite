
var menu_toggled = false;

var client_id = "va97w97mn1qzq0nlrjavlifr92lstz"; //Twitch-API Client ID
//https://static-cdn.jtvnw.net/user-default-pictures-uv/75305d54-c7cc-40d1-bb9c-91fbe85943c7-profile_image-150x150.png
var result_template = 
'<a class="result_card" href="https://www.twitch.tv/{NAME}">\
<img src="{THUMBNAIL}">\
<div class="gradient"></div>\
<img class="avatar" src="{AVATAR}">\
<p class="stream_username">{NAME}</p>\
<p class="stream_title">{TITLE}</p>\
<p class="stream_viewers">🕒<span class="uptime">{TIME}</span> 👁️{VIEWERS}</p>\
<p class="result_label">{INDEX}</p>\
</a>';


function updateNav(){ //Updates Navbar and currently displayed content based on URL hash path.

    menu_toggled ? toggleMenu() : {}

    if(location.hash === ""){location.hash = "#Home"};

    hash = location.hash.substr(1, location.hash.length).toLowerCase();

    navLinks = document.getElementById("nav_links").getElementsByTagName("a"); //Iterates through and updates nav links.

    for (let i = 0; i < navLinks.length; i++) { 

        let link = navLinks[i];

        let id = link.id.substr(4, link.id.length).toLowerCase();

        if (id === hash)

            link.className = "navlink nav_active";

        else

            link.className = "navlink";

    } 

    pages = document.getElementById("pages").getElementsByClassName("content_container"); //Iterates through and updates content divs.

    for (let i = 0; i < pages.length; i++) { 

        let page = pages[i];

        let id = page.id.substr(8, page.id.length).toLowerCase();

        if (id === hash)

            page.className = "content_container content_active";

        else

            page.className = "content_container";

    } 

}


const options = {

    responseType: 'json'

};

function validate(username){ //validate username with backend

    console.log("Making validation call to backend");

    axios.get('/validate/' + encodeURI(username), options).then(response => {
        data = Object.values(response.data);
        console.log(response);

        if (data.length > 0){

            location.hash = "#Results";
            location.search = "?id=" + document.getElementById("topsearch").value;
            
        }else{

            console.log("INVALID USERNAME");
            document.getElementById("midsearch").className = "home_searchbar invalid";
            document.getElementById("topsearch").className = "searchbar invalid";
        }

    });

}


function getStreams(username){ //Translate a given username into a twitch ID.

    console.log("Making call to backend");

    axios.get('/user/' + encodeURI(username), options).then(response => {
        data = Object.values(response.data);
        console.log(data);
        console.log(response);
        //console.log(response.type);
        if (data.length > 0){
            
            console.log("continuing");
            
            renderStreams(data.slice(0,10));

        }else{

            console.log("INVALID USERNAME");
        }

    });

}

function renderStreams(data){ //Generates html for displaying search results.

    let generatedHTML = '<div class="empty"></div>';

    data.map((stream, i) => {

        generatedHTML += result_template.replace("{TIME}", stream.stream_duration).replace("{AVATAR}", stream.profile_image_url).replace("{NAME}", stream.name).replace("{NAME}", stream.name).replace("{TITLE}", stream.stream_title).replace("{VIEWERS}", stream.viewer_count.toLocaleString()).replace("{THUMBNAIL}", stream.thumbnail_url.replace("{width}x{height}", "300x168")).replace("{INDEX}", i + 1);

    })

    document.getElementById("content_results").innerHTML += generatedHTML + '<div class="empty"></div>';

}



function init(){

    //Update both search bars when value is changed. Needs to be optimized/rewritten.
    let topsearch = document.getElementById("topsearch");
    let midsearch = document.getElementById("midsearch");
    topsearch.addEventListener("input", () => {midsearch.value = topsearch.value});
    midsearch.addEventListener("input", () => {topsearch.value = midsearch.value});


    //Handle firing of search function on form submission.
    document.getElementsByClassName("searchbar_wrapper")[0].addEventListener("submit", (event)=>{event.preventDefault(); search(event)});
    document.getElementsByClassName("searchbar_wrapper")[1].addEventListener("submit", (event)=>{event.preventDefault(); search(event)});

    //Handle mobile view menu button.
    document.getElementsByClassName("menu_button")[0].addEventListener("click", ()=>{toggleMenu()});


    //Check if url already contains username to search, whether from a saved bookmark or from submitting searchbar form.
    searchParams = new URLSearchParams(location.search);

    if(searchParams.has("id")){ //If there is a search query, update elements and perform get request for needed information.

        midsearch.value = searchParams.get("id");
        topsearch.value = searchParams.get("id");
        document.getElementById("nav_results").innerHTML = searchParams.get("id").toUpperCase();
        console.log("search params detected");
        getStreams(searchParams.get("id"));

    }
    
}

function toggleMenu(){

    menu_toggled = !menu_toggled;
    document.getElementById("nav_links").className = menu_toggled ? "navlinks menu_active" : "navlinks";

}

function search(event){

    validate(document.getElementById("topsearch").value);

}

window.addEventListener("load", () => {updateNav(); init()});
window.addEventListener("hashchange",() => updateNav());

