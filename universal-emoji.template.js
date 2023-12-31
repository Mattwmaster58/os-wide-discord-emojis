// noinspection JSUnresolvedReference
// @formatter:off
// {{autogenerated_warning}}
const EMOJI_DIR = "{{ emoji_dir }}";
const EMOJI_LOAD_LIMIT = parseInt("{{ emoji_load_limit }}");
const TAB_NAME = "Universal Emoji";
// @formatter:on

function emojiSearch(term) {
    paths = [];
    console.time("emoji searching");
    for (let fname of Dir(EMOJI_DIR).entryList()) {
        if (fname.endsWith(".gif") || fname.endsWith(".png")) {
            const [guild, name, extension] = fname.split(".");
            const score = scoreMatch(term, guild, name);
            if (score > 0) {
                paths.push({path: EMOJI_DIR + "/" + fname, guild, name, extension, score});
            }
        }
    }
    console.timeEnd("emoji searching");
    paths.sort((a, b) => {
        const [c1a, c1b] = [a.score, b.score];
        const c2 = a.name.localeCompare(b.name);
        const c3 = a.guild.localeCompare(b.guild);
        return (c1a - c1b) || c2 || c3;
    }).reverse();
    return paths
}

function scoreMatch(term, guild, name) {
    let score = 0;
    name = name.toLowerCase();
    guild = guild.toLowerCase();
    term = term.toLowerCase();
    if (name.startsWith(term)) {
        score = 4;
    } else if (name.includes(term)) {
        score = 3;
    } else if (guild.startsWith(term)) {
        score = 2;
    } else if (guild.includes(term)) {
        score = 1;
    }
    return score;
}

function loadEmojis(emojiObjs) {
    let totalBytesRead = 0;
    let i = 0;
    let clampedSizeEmojiList = emojiObjs.slice(0, EMOJI_LOAD_LIMIT);
    let seenEmojiHashes = new Set();
    for (const emojiObj of emojiObjs) {
        console.debug("loading:", JSON.stringify(emojiObj));
        const emojiFile = new File(emojiObj.path);
        if (!emojiFile.openReadOnly()) {
            throw `failed to open Emoji file ${emojiObj.path}, quitting early`;
            // noinspection UnreachableCodeJS
            // i think we continue through errors in Qt's runtime, thus this is reachable
            break;
        }
        const tags = `${emojiObj.name},${emojiObj.guild},${emojiObj.extension}`;
        const emojiBytes = emojiFile.readAll();
        if (emojiBytes.length === 0) {
            console.log(`warning: emoji file is empty. Did the downloader fail? ${emojiObj}`);
            continue;
        }
        const emojiMd5 = md5sum(emojiBytes);
        if (!seenEmojiHashes.has(emojiMd5)) {
            seenEmojiHashes.add(emojiMd5);
            totalBytesRead += emojiBytes.length;
            insert(++i, {
                "application/x-copyq-tags": tags,
                // this will onnly be used by apps when it's a GIF
                "text/uri-list": `file:///${emojiObj.path}`,
                // this will only be used by apps when it's a PNG, but it's necessary to include to preview gifs
                [`image/${emojiObj.extension}`]: emojiBytes,
            });
            if (i > EMOJI_LOAD_LIMIT) {
                console.log(`loaded the limit of ${EMOJI_LOAD_LIMIT}`);
                break;
            }
        } else {
            console.log(`skipping byte-for-byte identical emoji ${tags}`);
        }
    }
    console.log(`read cumulative ${totalBytesRead}b for ${clampedSizeEmojiList.length} emojis`);
}

const emojiSearchTerm = dialog(
    ...['.title', "Search Emoji"],
    "Enter emoji search term",
);

if (emojiSearchTerm) {
    console.log(`searching with term: ${JSON.stringify(emojiSearchTerm)}`);
    try {
        console.log("clearing search result tab prior to search");
        // could've been removed by user before we do it ourselves
        removeTab(TAB_NAME);
    } catch (e) {
        console.log("tab already does not exist");
    }
    const emojis = emojiSearch(emojiSearchTerm);
    if (emojis.length === 0) {
        popup("0 results", `No search results found for search term "${emojiSearchTerm}"`);
    } else {
        // this sets where we insert + select the tab in the gui
        tab(TAB_NAME);
        setCurrentTab(TAB_NAME);
        console.log(`loading ${emojis.length} emojis to clipboard`);
        loadEmojis(emojis, TAB_NAME);
        console.log("waiting for window to close");
        showAt();
        while (true) {
            while (visible()) sleep(75);
            console.log("window no longer visible, waiting additional grace period before clearing");
            sleep(2000);
            if (!visible()) {
                break;
            } else {
                console.log("window was re-opened within the grace period, deferring tab removal for now");
            }
        }
        try {
            // could've been removed by user before we do it ourselves
            removeTab(TAB_NAME);
        } catch (e) {
            console.log("tab was removed before we could do it ourselves");
        }
    }
} else {
    console.log("no search term inputted");
}
