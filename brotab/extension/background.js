/*
On startup, connect to the "brotab_mediator" app.
*/

const GET_WORDS_SCRIPT = '[...new Set(document.body.innerText.match(/\\w+/g))].sort().join("\\n");'


class BrowserTabs {
  constructor(browser) {
    this._browser = browser;
  }

  list(onSuccess) {
    throw new Error('list is not implemented');
  }

  close(tab_ids) {
    this._browser.tabs.remove(tab_ids);
  }

  move(tabId, moveOptions, onSuccess) {
    throw new Error('move is not implemented');
  }

  create(createOptions) {
    throw new Error('create is not implemented');
  }

  activate(tab_id) {
    this._browser.tabs.update(tab_id, {'active': true});
  }

  getActive(onSuccess) {
    throw new Error('getActive is not implemented');
  }

  getWords(tab_id, onSuccess, onError) {
    throw new Error('getWords is not implemented');
  }
}

class FirefoxTabs extends BrowserTabs {
  list(onSuccess) {
    this._browser.tabs.query({}).then(
      onSuccess,
      (error) => console.log(`Error listing tabs: ${error}`)
    );
  }

  move(tabId, moveOptions, onSuccess) {
    this._browser.tabs.move(tabId, moveOptions).then(
      onSuccess,
      // (tab) => console.log(`Moved: ${tab}`),
      (error) => console.log(`Error moving tab: ${error}`)
    );
  }

  create(createOptions) {
    this._browser.tabs.create(createOptions).then(
      (tab) => console.log(`Created new tab: ${tab.id}`),
      (error) => console.log(`Error: ${error}`)
    );
  }

  getActive(onSuccess) {
    this._browser.tabs.query({active: true}).then(
      onSuccess,
      (error) => console.log(`Error: ${error}`)
    );
  }

  getWords(tab_id, onSuccess, onError) {
    this._browser.tabs.executeScript(tab_id, {code: GET_WORDS_SCRIPT}).then(
      onSuccess,
      onError
    );
  }
}

class ChromeTabs extends BrowserTabs {
  list(onSuccess) {
    this._browser.tabs.query({}, onSuccess);
  }

  move(tabId, moveOptions, onSuccess) {
    this._browser.tabs.move(tabId, moveOptions, onSuccess);
  }

  create(createOptions) {
    this._browser.tabs.create(createOptions,
      (tab) => console.log(`Created new tab: ${tab.id}`)
    );
  }

  getActive(onSuccess) {
    this._browser.tabs.query({active: true}, onSuccess);
  }

  getWords(tab_id, onSuccess, onError) {
    this._browser.tabs.executeScript(
      tab_id, {code: GET_WORDS_SCRIPT},
      (result) => {
        // https://stackoverflow.com/a/45603880/258421
        let lastError = chrome.runtime.lastError;
        if (lastError) {
          onError(lastError);
        } else {
          onSuccess(result);
        }
      }
    );
  }
}


console.log("Detecting browser");
var port = undefined;
var tabs = undefined;
const NATIVE_APP_NAME = 'brotab_mediator';

if (typeof browser !== 'undefined') {
  port = browser.runtime.connectNative(NATIVE_APP_NAME);
  console.log("It's Firefox: " + port);
  browserTabs = new FirefoxTabs(browser);

} else if (typeof chrome !== 'undefined') {
  port = chrome.runtime.connectNative(NATIVE_APP_NAME);
  console.log("It's Chrome/Chromium: " + port);
  browserTabs = new ChromeTabs(chrome);

} else {
  console.error("Unknown browser detected");
}


// see https://stackoverflow.com/a/15479354/258421
// function naturalCompare(a, b) {
//     var ax = [], bx = [];

//     a.replace(/(\d+)|(\D+)/g, function(_, $1, $2) { ax.push([$1 || Infinity, $2 || ""]) });
//     b.replace(/(\d+)|(\D+)/g, function(_, $1, $2) { bx.push([$1 || Infinity, $2 || ""]) });

//     while(ax.length && bx.length) {
//         var an = ax.shift();
//         var bn = bx.shift();
//         var nn = (an[0] - bn[0]) || an[1].localeCompare(bn[1]);
//         if(nn) return nn;
//     }

//     return ax.length - bx.length;
// }

function compareWindowIdTabId(tabA, tabB) {
  if (tabA.windowId != tabB.windowId) {
    return tabA.windowId - tabB.windowId;
  }
  return tabA.index - tabB.index;
}

function listTabsOnSuccess(tabs) {
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

function listTabs() {
  browserTabs.list(listTabsOnSuccess);
}

// function moveTabs(move_triplets) {
//   for (let triplet of move_triplets) {
//     const [tabId, windowId, index] = triplet;
//     browserTabs.move(tabId, {index: index, windowId: windowId});
//   }
// }

function moveTabs(move_triplets) {
  if (move_triplets.length == 0) {
    return
  }

  const [tabId, windowId, index] = move_triplets[0];
  browserTabs.move(tabId, {index: index, windowId: windowId},
    (tab) => moveTabs(move_triplets.slice(1)));
}

function closeTabs(tab_ids) {
  browserTabs.close(tab_ids);
}

function openUrls(urls, window_id) {
  for (let url of urls) {
    browserTabs.create({'url': url, windowId: window_id});
  }
}

function createTab(url) {
  browserTabs.create({'url': url});
}

function activateTab(tab_id) {
  browserTabs.activate(tab_id);
}

function getWordsFromTabs(tabs) {
  var promises = [];
  console.log(`Getting words from tabs: ${tabs}`);

  for (let tab of tabs) {
    var promise = new Promise(
      (resolve, reject) => browserTabs.getWords(tab.id,
        (words) => {
          console.log(`Got ${words.length} words from another tab`);
          resolve(words);
        },
        (error) => {
          console.log(`Could not get words from tab: ${error}`);
          resolve([]);
        })
    );
    promises.push(promise);
  }
  Promise.all(promises).then(
    (all_words) => {
      const result = Array.prototype.concat(...all_words);
      console.log(`Total number of words: ${result.length}`);
      port.postMessage(result);
    }
  )
}

function getWords(tab_id) {
  if (tab_id == null) {
    browserTabs.getActive(getWordsFromTabs);
  } else {
    browserTabs.getWords(tab_id,
      (words) => port.postMessage(words));
  }
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

  else if (command['name'] == 'open_urls') {
    console.log('Opening URLs:', command['urls'], command['window_id']);
    openUrls(command['urls'], command['window_id']);
  }

  else if (command['name'] == 'new_tab') {
    console.log('Creating tab:', command['url']);
    createTab(command['url']);
  }

  else if (command['name'] == 'activate_tab') {
    console.log('Activating tab:', command['tab_id']);
    activateTab(command['tab_id']);
  }

  else if (command['name'] == 'get_words') {
    console.log('Getting words from tab:', command['tab_id']);
    getWords(command['tab_id']);
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
