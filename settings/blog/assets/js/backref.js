function backrefs (){
    let root_url = window.location.origin + window.location.pathname;
    let links = document.getElementsByTagName("a");
    var refs = [];
    for (let x of links){
        if (x.href.replace(root_url, "").startsWith("#ref-")){
            let ref = x.href.replace(root_url, "").replace("#", "");
            let backref = ref.replace("ref-", "backref-");
            if (! refs.includes(ref)){
                refs.push(ref);
            } else{
                let num = refs.filter(x => x === ref).length;
                backref = backref + "-" + String(num);
            }
            x.setAttribute("id", backref);
            let child = document.createElement("a");
            child.setAttribute("href", "#" + backref);
            child.textContent = "\xa0^";
            document.getElementById(ref).children[0].appendChild(child);
        }
    }
}
