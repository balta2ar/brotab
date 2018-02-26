/*
On startup, connect to the "firefox_mediator" app.
*/

console.log("Detecting browser");
var port = undefined;

if (typeof browser !== 'undefined') {
  port = browser.runtime.connectNative("brotab_mediator");
  console.log("It's Firefox: " + port);

  var listTabs = listTabsFirefox;
  var moveTabs = moveTabsFirefox;

} else if (typeof chrome !== 'undefined') {
  port = chrome.runtime.connectNative("brotab_mediator");
  console.log("It's Chrome/Chromium: " + port);

  var browser = chrome;
  var listTabs = listTabsChrome;
  var moveTabs = moveTabsChrome;

} else {
  console.error("Unknown browser detected");
}


// see https://stackoverflow.com/a/15479354/258421
function naturalCompare(a, b) {
    var ax = [], bx = [];

    a.replace(/(\d+)|(\D+)/g, function(_, $1, $2) { ax.push([$1 || Infinity, $2 || ""]) });
    b.replace(/(\d+)|(\D+)/g, function(_, $1, $2) { bx.push([$1 || Infinity, $2 || ""]) });

    while(ax.length && bx.length) {
        var an = ax.shift();
        var bn = bx.shift();
        var nn = (an[0] - bn[0]) || an[1].localeCompare(bn[1]);
        if(nn) return nn;
    }

    return ax.length - bx.length;
}

function compareWindowIdTabId(a, b) {
  // (a, b) => [a.windowId, a.index] > [b.windowId, b.index]
  if (a.windowId != b.windowId) {
    return a.windowId - b.windowId;
  }
  return a.index - b.index;
}

function listTabsSuccess(tabs) {
  lines = [];
  // Make sure tabs are sorted by their index within a window
  tabs.sort(compareWindowIdTabId);
  for (let tab of tabs) {
    line = + tab.windowId + "." + tab.id + "\t" + tab.title + "\t" + tab.url;
    console.log(line);
    lines.push(line);
  }
  // lines = lines.sort(naturalCompare);
  port.postMessage(lines);
}

function listTabsError(error) {
  console.log(`Error: ${error}`);
}

function listTabsFirefox() {
  browser.tabs.query({}).then(listTabsSuccess, listTabsError);
}

function listTabsChrome() {
  chrome.tabs.query({}, listTabsSuccess);
}

function closeTabs(tab_ids) {
  browser.tabs.remove(tab_ids);
}

function moveTabsFirefox(move_triplets) {
  for (let triplet of move_triplets) {
    const [tabId, windowId, index] = triplet;
    browser.tabs.move(tabId, {index: index, windowId: windowId}).then(
      (tab) => console.log(`Moved: ${tab}`),
      (error) => console.log(`Error moving tab: ${error}`)
    )
  }
}

function moveTabsChrome(move_triplets) {
  for (let triplet of move_triplets) {
    const [tabId, windowId, index] = triplet;
    browser.tabs.move(tabId, {index: index, windowId: windowId},
      (tab) => console.log(`Moved: ${tab}`));
  }
}

function createTab(url) {
  browser.tabs.create({'url': url})
}

function activateTab(tab_id) {
  browser.tabs.update(tab_id, {'active': true})
}

/*
Listen for messages from the app.
*/
port.onMessage.addListener((command) => {
  console.log("Received: " + JSON.stringify(command, null, 4));

  if (command['name'] == 'list_tabs') {
    console.log('Listing tabs...');
    listTabs();
  }

  else if (command['name'] == 'close_tabs') {
    console.log('Closing tabs:', command['tab_ids']);
    closeTabs(command['tab_ids']);
  }

  else if (command['name'] == 'move_tabs') {
    console.log('Moving tabs:', command['move_triplets']);
    moveTabs(command['move_triplets']);
  }

  else if (command['name'] == 'new_tab') {
    console.log('Creating tab:', command['url']);
    createTab(command['url']);
  }

  else if (command['name'] == 'activate_tab') {
    console.log('Activating tab:', command['tab_id']);
    activateTab(command['tab_id']);
  }
});

port.onDisconnect.addListener(function() {
  console.log("Disconnected");
});

console.log("Connected to native app");

/*
On a click on the browser action, send the app a message.
*/
// browser.browserAction.onClicked.addListener(() => {
//   // console.log("Sending:  ping");
//   // port.postMessage("ping");
//
//   console.log('Listing tabs');
//   listTabs();
// });
