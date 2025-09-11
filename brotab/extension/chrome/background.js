/*
On startup, connect to the "brotab_mediator" app.
*/

//const GET_WORDS_SCRIPT = '[...new Set(document.body.innerText.match(/\\w+/g))].sort().join("\\n");';
const GET_WORDS_SCRIPT = '[...new Set(document.documentElement.innerText.match(#match_regex#))].sort().join(#join_with#);';
//const GET_TEXT_SCRIPT = 'document.body.innerText.replace(/\\n|\\r|\\t/g, " ");';
const GET_TEXT_SCRIPT = 'document.documentElement.innerText.replace(#delimiter_regex#, #replace_with#);';
const GET_HTML_SCRIPT = 'document.documentElement.innerHTML.replace(#delimiter_regex#, #replace_with#);';


class BrowserTabs {
  constructor(browser) {
    this._browser = browser;
  }

  runtime() {
    return this._browser.runtime;
  }

  list(queryInfo, onSuccess) {
    throw new Error('list is not implemented');
  }

  query(queryInfo, onSuccess) {
    throw new Error('query is not implemented');
  }

  close(tab_ids, onSuccess) {
    throw new Error('close is not implemented');
  }

  move(tabId, moveOptions, onSuccess) {
    throw new Error('move is not implemented');
  }

  update(tabId, options, onSuccess, onError) {
    throw new Error('update is not implemented');
  }

  create(createOptions, onSuccess) {
    throw new Error('create is not implemented');
  }

  activate(tab_id) {
    throw new Error('activate is not implemented');
  }

  getActive(onSuccess) {
    throw new Error('getActive is not implemented');
  }

  getActiveScreenshot(onSuccess) {
    throw new Error('getActiveScreenshot is not implemented');
  }

  runScript(tab_id, script, payload, onSuccess, onError) {
    throw new Error('runScript is not implemented');
  }

  getBrowserName() {
    throw new Error('getBrowserName is not implemented');
  }
}

class FirefoxTabs extends BrowserTabs {
  list(queryInfo, onSuccess) {
    this._browser.tabs.query(queryInfo).then(
      onSuccess,
      (error) => console.log(`Error listing tabs: ${error}`)
    );
  }

  query(queryInfo, onSuccess) {
    if (queryInfo.hasOwnProperty('windowFocused')) {
      let keepFocused = queryInfo['windowFocused']
      delete queryInfo.windowFocused;
      this._browser.tabs.query(queryInfo).then(
        tabs => {
          Promise.all(tabs.map(tab => {
            return new Promise(resolve => {
              this._browser.windows.get(tab.windowId, {populate: false}, window => {
                resolve(window.focused === keepFocused ? tab : null);
              });
            });
          })).then(result => {
            tabs = result.filter(tab => tab !== null);
            onSuccess(tabs);
          });
        },
        (error) => console.log(`Error executing queryTabs: ${error}`)
      );
    } else {
      this._browser.tabs.query(queryInfo).then(
        onSuccess,
        (error) => console.log(`Error executing queryTabs: ${error}`)
      );
    }
  }

  close(tab_ids, onSuccess) {
    this._browser.tabs.remove(tab_ids).then(
      onSuccess,
      (error) => console.log(`Error removing tab: ${error}`)
    );
  }

  move(tabId, moveOptions, onSuccess) {
    this._browser.tabs.move(tabId, moveOptions).then(
      onSuccess,
      // (tab) => console.log(`Moved: ${tab}`),
      (error) => console.log(`Error moving tab: ${error}`)
    );
  }

  update(tabId, options, onSuccess, onError) {
    this._browser.tabs.update(tabId, options).then(
      onSuccess,
      (error) => {
        console.log(`Error updating tab ${tabId}: ${error}`)
        onError(error)
      }
    );
  }

  create(createOptions, onSuccess) {
    if (createOptions.windowId === 0) {
      this._browser.windows.create({ url: createOptions.url }).then(
        onSuccess,
        (error) => console.log(`Error: ${error}`)
      );
    } else {
      this._browser.tabs.create(createOptions).then(
        onSuccess,
        (error) => console.log(`Error: ${error}`)
      );
    }
  }

  getActive(onSuccess) {
    this._browser.tabs.query({active: true}).then(
      onSuccess,
      (error) => console.log(`Error: ${error}`)
    );
  }

  getActiveScreenshot(onSuccess) {
    let queryOptions = { active: true, lastFocusedWindow: true };
    this._browser.tabs.query(queryOptions).then(
      (tabs) => {
        let tab = tabs[0];
        let windowId = tab.windowId;
        let tabId = tab.id;
        this._browser.tabs.captureVisibleTab(windowId, { format: 'png' }).then(
          function(data) {
            const message = {
              tab: tabId,
              window: windowId,
              data: data
            };
            onSuccess(message);
          },
          (error) => console.log(`Error: ${error}`)
        );
      },
      (error) => console.log(`Error: ${error}`)
    );
  }

  runScript(tab_id, script, payload, onSuccess, onError) {
    this._browser.tabs.executeScript(tab_id, {code: script}).then(
      (result) => onSuccess(result, payload),
      (error) => onError(error, payload)
    );
  }

  getBrowserName() {
      return "firefox";
  }

  activate(tab_id, focused) {
    this._browser.tabs.update(tab_id, {'active': true});
    this._browser.tabs.get(tab_id, function(tab) {
      browser.windows.update(tab.windowId, {focused: focused});
    });
  }
}

class ChromeTabs extends BrowserTabs {
  list(queryInfo, onSuccess) {
    this._browser.tabs.query(queryInfo, onSuccess);
  }

  activate(tab_id, focused) {
    this._browser.tabs.update(tab_id, {'active': true});
    this._browser.tabs.get(tab_id, function(tab) {
      chrome.windows.update(tab.windowId, {focused: focused});
    });
  }

  query(queryInfo, onSuccess) {
    if (queryInfo.hasOwnProperty('windowFocused')) {
      let keepFocused = queryInfo['windowFocused']
      delete queryInfo.windowFocused;
      this._browser.tabs.query(queryInfo, tabs => {
        Promise.all(tabs.map(tab => {
          return new Promise(resolve => {
            this._browser.windows.get(tab.windowId, {populate: false}, window => {
              resolve(window.focused === keepFocused ? tab : null);
            });
          });
        })).then(result => {
          tabs = result.filter(tab => tab !== null);
          onSuccess(tabs);
        });
      });
    } else {
      this._browser.tabs.query(queryInfo, onSuccess);
    }
  }

  close(tab_ids, onSuccess) {
    this._browser.tabs.remove(tab_ids, onSuccess);
  }

  move(tabId, moveOptions, onSuccess) {
    this._browser.tabs.move(tabId, moveOptions, onSuccess);
  }

  update(tabId, options, onSuccess, onError) {
    this._browser.tabs.update(tabId, options, tab => {
      if (this._browser.runtime.lastError) {
        let error = this._browser.runtime.lastError.message;
        console.error(`Could not update tab: ${error}, tabId=${tabId}, options=${JSON.stringify(options)}`)
        onError(error)
      } else {
        onSuccess(tab)
      }
    });
  }

  create(createOptions, onSuccess) {
    if (createOptions.windowId === 0) {
      this._browser.windows.create({ url: createOptions.url }, onSuccess);
    } else {
      this._browser.tabs.create(createOptions, onSuccess);
    }
  }

  getActive(onSuccess) {
    this._browser.tabs.query({active: true}, onSuccess);
  }

  getActiveScreenshot(onSuccess) {
    // this._browser.tabs.captureVisibleTab(null, { format: 'png' }, onSuccess);
    let queryOptions = { active: true, lastFocusedWindow: true };
    this._browser.tabs.query(queryOptions, (tabs) => {
      let tab = tabs[0];
      let windowId = tab.windowId;
      let tabId = tab.id;
      this._browser.tabs.captureVisibleTab(windowId, { format: 'png' }, function(data) {
        const message = {
          tab: tabId,
          window: windowId,
          data: data
        };
        onSuccess(message);
      });
    });
  }

  runScript(tab_id, script, payload, onSuccess, onError) {
    // Manifest V3: use chrome.scripting.executeScript instead of tabs.executeScript
    this._browser.scripting.executeScript(
      {
        target: { tabId: tab_id },
        func: (code) => {
          // Execute provided code string in the page context
          // and return its result. This mirrors MV2 behavior where
          // executeScript returned an array with a single result.
          // eslint-disable-next-line no-eval
          return eval(code);
        },
        args: [script]
      },
      (injectionResults) => {
        const lastError = chrome.runtime.lastError;
        if (lastError) {
          onError(lastError, payload);
        } else {
          const results = (injectionResults || []).map(r => r.result);
          onSuccess(results, payload);
        }
      }
    );
  }

  getBrowserName() {
      return "chrome/chromium";
  }
}


console.log("Detecting browser");
var port = undefined;
var tabs = undefined;
var browserTabs = undefined;
const NATIVE_APP_NAME = 'brotab_mediator';
reconnect();

// In MV3, the service worker can be suspended when idle.
// Use an alarm to periodically wake it and re-establish the native connection
// without sending unsolicited messages to the native app.
try {
  if (typeof chrome !== 'undefined' && chrome.alarms) {
    const KEEPALIVE_ALARM = 'bt-keepalive';

    function scheduleKeepAlive() {
      // Minimum is 1 minute; keep it modest to avoid excessive wakeups
      chrome.alarms.create(KEEPALIVE_ALARM, { periodInMinutes: 1 });
    }

    chrome.runtime.onInstalled.addListener(() => {
      scheduleKeepAlive();
      // Ensure we have a connection on install/refresh
      if (!port) reconnect();
    });

    chrome.runtime.onStartup.addListener(() => {
      scheduleKeepAlive();
      // Ensure we have a connection on browser startup
      if (!port) reconnect();
    });

    chrome.alarms.onAlarm.addListener((alarm) => {
      if (alarm && alarm.name === KEEPALIVE_ALARM) {
        // If there is no active port, re-connect; do not send messages
        if (!port) reconnect();
      }
    });
  }
} catch (e) {
  console.warn('Keepalive scheduling failed:', e);
}

function reconnect() {
  console.log("Connecting to native app");
  if (typeof browser !== 'undefined') {
    port = browser.runtime.connectNative(NATIVE_APP_NAME);
    console.log("It's Firefox: " + port);
    browserTabs = new FirefoxTabs(browser);

  } else if (typeof chrome !== 'undefined') {
    port = chrome.runtime.connectNative(NATIVE_APP_NAME);
    console.log("It's Chrome/Chromium: " + port);
    browserTabs = new ChromeTabs(chrome);

  } else {
    console.log("Unknown browser detected");
  }
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
  var lines = [];
  // Make sure tabs are sorted by their index within a window
  tabs.sort(compareWindowIdTabId);
  for (let tab of tabs) {
    var line = + tab.windowId + "." + tab.id + "\t" + tab.title + "\t" + tab.url;
    console.log(line);
    lines.push(line);
  }
  // lines = lines.sort(naturalCompare);
  port.postMessage(lines);
}

function listTabs() {
  browserTabs.list({}, listTabsOnSuccess);
}

function queryTabsOnSuccess(tabs) {
  tabs.sort(compareWindowIdTabId);
  let lines = tabs.map(tab => `${tab.windowId}.${tab.id}\t${tab.title}\t${tab.url}`)
  console.log(lines);
  port.postMessage(lines);
}

function queryTabsOnFailure(error) {
  console.error(error);
  port.postMessage([]);
}

function queryTabs(query_info) {
  try {
    let query = atob(query_info)
    query = JSON.parse(query)

    integerKeys = {'windowId': null, 'index': null};
    booleanKeys = {'active': null, 'pinned': null, 'audible': null, 'muted': null, 'highlighted': null,
      'discarded': null, 'autoDiscardable': null, 'currentWindow': null, 'lastFocusedWindow': null, 'windowFocused': null};

    query = Object.entries(query).reduce((o, [k,v]) => {
      if (booleanKeys.hasOwnProperty(k) && typeof v != 'boolean') {
        if (v.toLowerCase() == 'true')
          o[k] = true;
        else if (v.toLowerCase() == 'false')
          o[k] = false;
        else
          o[k] = v;
      }
      else if (integerKeys.hasOwnProperty(k) && typeof v != 'number')
        o[k] = Number(v);
      else
        o[k] = v;
      return o;
    }, {})

    browserTabs.query(query, queryTabsOnSuccess);
  }
  catch(error) {
    queryTabsOnFailure(error);
  }
}

// function moveTabs(move_triplets) {
//   for (let triplet of move_triplets) {
//     const [tabId, windowId, index] = triplet;
//     browserTabs.move(tabId, {index: index, windowId: windowId});
//   }
// }

function moveTabs(move_triplets) {
  // move_triplets is a tuple of (tab_id, window_id, new_index)
  if (move_triplets.length == 0) {
    // this post is only required to make bt move command synchronous. mediator
    // is waiting for any reply
    port.postMessage('OK');
    return
  }

  // we request a move of a single tab and when it happens, we call ourselves
  // again with the remaining tabs (first omitted)
  const [tabId, windowId, index] = move_triplets[0];
  browserTabs.move(tabId, {index: index, windowId: windowId},
    (tab) => moveTabs(move_triplets.slice(1))
  );
}

function closeTabs(tab_ids) {
  browserTabs.close(tab_ids, () => port.postMessage('OK'));
}

function openUrls(urls, window_id, first_result="") {
  if (urls.length == 0) {
    console.log('Opening urls done');
    port.postMessage([]);
    return;
  }

  if (window_id === 0) {
    browserTabs.create({'url': urls[0], windowId: 0}, (window) => {
      result = `${window.id}.${window.tabs[0].id}`;
      console.log(`Opened first window: ${result}`);
      urls = urls.slice(1);
      openUrls(urls, window.id, result);
    });
    return;
  }

  var promises = [];
  for (let url of urls) {
    console.log(`Opening another one url ${url}`);
    promises.push(new Promise((resolve, reject) => {
      browserTabs.create({'url': url, windowId: window_id},
        (tab) => resolve(`${tab.windowId}.${tab.id}`)
      );
    }))
  };
  Promise.all(promises).then(result => {
    if (first_result !== "") {
      result.unshift(first_result);
    }
    const data = Array.prototype.concat(...result)
    console.log(`Sending ids back: ${JSON.stringify(data)}`);
    port.postMessage(data)
  });
}

function createTab(url) {
  browserTabs.create({'url': url},
    (tab) => {
      console.log(`Created new tab: ${tab.id}`);
      port.postMessage([`${tab.windowId}.${tab.id}`]);
  });
}

function updateTabs(updates) {
  if (updates.length == 0) {
    console.log('Updating tabs done');
    port.postMessage([]);
    return;
  }

  var promises = [];
  for (let update of updates) {
    console.log(`Updating tab ${JSON.stringify(update)}`);
    promises.push(new Promise((resolve, reject) => {
      browserTabs.update(update.tab_id, update.properties,
        (tab) => { resolve(`${tab.windowId}.${tab.id}`) },
        (error) => {
          console.error(`Could not update tab: ${error}, update=${JSON.stringify(update)}`)
          resolve()
        }
      );
    }))
  };
  Promise.all(promises).then(result => {
    const data = Array.prototype.concat(...result).filter(x => !!x)
    console.log(`Sending ids back after update: ${JSON.stringify(data)}`);
    port.postMessage(data)
  });
}

function activateTab(tab_id, focused) {
  browserTabs.activate(tab_id, focused);
}

function getActiveTabs() {
  browserTabs.getActive(tabs => {
      var result = tabs.map(tab => tab.windowId + "." + tab.id).toString()
      console.log(`Active tabs: ${result}`);
      port.postMessage(result);
  });
}

function getActiveScreenshot() {
  browserTabs.getActiveScreenshot(data => {
    port.postMessage(data);
  });
}

function getWordsScript(match_regex, join_with) {
  return GET_WORDS_SCRIPT
    .replace('#match_regex#', match_regex)
    .replace('#join_with#', join_with);
}

function getTextScript(delimiter_regex, replace_with) {
  return GET_TEXT_SCRIPT
    .replace('#delimiter_regex#', delimiter_regex)
    .replace('#replace_with#', replace_with);
}

function getHtmlScript(delimiter_regex, replace_with) {
  return GET_HTML_SCRIPT
    .replace('#delimiter_regex#', delimiter_regex)
    .replace('#replace_with#', replace_with);
}

function listOr(list, default_value) {
  if ((list.length == 1) && (list[0] == null)) {
    return default_value;
  }
  return list;
}

function getWordsFromTabs(tabs, match_regex, join_with) {
  var promises = [];
  console.log(`Getting words from tabs: ${tabs}`);
  const script = getWordsScript(match_regex, join_with);

  for (let tab of tabs) {
    var promise = new Promise(
      (resolve, reject) => browserTabs.runScript(tab.id, script, null,
        (words, _payload) => {
          words = listOr(words, []);
          console.log(`Got ${words.length} words from another tab`);
          resolve(words);
        },
        (error, _payload) => {
          console.log(`Could not get words from tab: ${error}`);
          resolve([]);
        }
      )
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

function getWords(tab_id, match_regex, join_with) {
  if (tab_id == null) {
    console.log(`Getting words for active tabs`);
    browserTabs.getActive(
      (tabs) => getWordsFromTabs(tabs, match_regex, join_with),
    );
  } else {
    const script = getWordsScript(match_regex, join_with);
    console.log(`Getting words, running a script: ${script}`);
    browserTabs.runScript(tab_id, script, null,
      (words, _payload) => port.postMessage(listOr(words, [])),
      (error, _payload) => console.log(`getWords: tab_id=${tab_id}, could not run script (${script})`),
    );
  }
}

function getTextOrHtmlFromTabs(tabs, scriptGetter, delimiter_regex, replace_with, onSuccess) {
  var promises = [];
  const script = scriptGetter(delimiter_regex, replace_with)
  console.log(`Getting text from tabs: ${tabs.length}, script (${script})`);

  lines = [];
  for (let tab of tabs) {
    // console.log(`Processing tab ${tab.id}`);
    var promise = new Promise(
      (resolve, reject) => browserTabs.runScript(tab.id, script, tab,
        (text, current_tab) => {
          // let as_text = JSON.stringify(text);
          // I don't know why, but an array of one item is sent here, so I take
          // the first item.
          if (text && text[0]) {
            console.log(`Got ${text.length} chars of text from another tab: ${current_tab.id}`);
            resolve({tab: current_tab, text: text[0]});
          } else {
            console.log(`Got empty text from another tab: ${current_tab.id}`);
            resolve({tab: current_tab, text: ''});
          }
        },
        (error, current_tab) => {
          console.log(`Could not get text from tab: ${error}: ${current_tab.id}`);
          resolve({tab: current_tab, text: ''});
        }
      )
    );
    promises.push(promise);
  }

  Promise.all(promises).then(onSuccess);
}

function getTextOnRunScriptSuccess(all_results) {
  console.log(`Ready`);
  console.log(`Text promises are ready: ${all_results.length}`);
  // console.log(`All results: ${JSON.stringify(all_results)}`);
  lines = [];
  for (let result of all_results) {
    // console.log(`result: ${result}`);
    tab = result['tab'];
    text = result['text'];
    // console.log(`Result: ${tab.id}, ${text.length}`);
    let line = tab.windowId + "." + tab.id + "\t" + tab.title + "\t" + tab.url + "\t" + text;
    lines.push(line);
  }
  // lines = lines.sort(naturalCompare);
  console.log(`Total number of lines of text: ${lines.length}`);
  port.postMessage(lines);
}

function getTextOnListSuccess(tabs, delimiter_regex, replace_with) {
  // Make sure tabs are sorted by their index within a window
  tabs.sort(compareWindowIdTabId);
  getTextOrHtmlFromTabs(tabs, getTextScript, delimiter_regex, replace_with, getTextOnRunScriptSuccess);
}

function getText(delimiter_regex, replace_with) {
  browserTabs.list({'discarded': false},
      (tabs) => getTextOnListSuccess(tabs, delimiter_regex, replace_with),
  );
}

function getHtmlOnListSuccess(tabs, delimiter_regex, replace_with) {
  // Make sure tabs are sorted by their index within a window
  tabs.sort(compareWindowIdTabId);
  getTextOrHtmlFromTabs(tabs, getHtmlScript, delimiter_regex, replace_with, getTextOnRunScriptSuccess);
}

function getHtml(delimiter_regex, replace_with) {
  browserTabs.list({'discarded': false},
      (tabs) => getHtmlOnListSuccess(tabs, delimiter_regex, replace_with),
  );
}

function getBrowserName() {
  const name = browserTabs.getBrowserName();
  console.log("Sending browser name: " + name);
  port.postMessage(name);
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

  else if (command['name'] == 'query_tabs') {
    console.log('Querying tabs...');
    queryTabs(command['query_info']);
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

  else if (command['name'] == 'update_tabs') {
    console.log('Updating tabs:', command['updates']);
    updateTabs(command['updates']);
  }

  else if (command['name'] == 'activate_tab') {
    console.log('Activating tab:', command['tab_id']);
    activateTab(command['tab_id'], !!command['focused']);
  }

  else if (command['name'] == 'get_active_tabs') {
    console.log('Getting active tabs');
    getActiveTabs();
  }

  else if (command['name'] == 'get_screenshot') {
    console.log('Getting visible screenshot');
    getActiveScreenshot();
  }

  else if (command['name'] == 'get_words') {
    console.log('Getting words from tab:', command['tab_id']);
    getWords(command['tab_id'], command['match_regex'], command['join_with']);
  }

  else if (command['name'] == 'get_text') {
    console.log('Getting texts from all tabs');
    getText(command['delimiter_regex'], command['replace_with']);
  }

  else if (command['name'] == 'get_html') {
    console.log('Getting HTML from all tabs');
    getHtml(command['delimiter_regex'], command['replace_with']);
  }

  else if (command['name'] == 'get_browser') {
    console.log('Getting browser name');
    getBrowserName();
  }
});

port.onDisconnect.addListener(function() {
  console.log("Disconnected");
  if(chrome.runtime.lastError) {
    console.warn("Reason: " + chrome.runtime.lastError.message);
  } else {
    console.warn("lastError is undefined");
  }
  //sleep(5000);
  console.log("Trying to reconnect");
  reconnect();
});

console.log("Connected to native app " + NATIVE_APP_NAME);

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
