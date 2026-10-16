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

  getActiveScreenshot(onSuccess, onError) {
    throw new Error('getActiveScreenshot is not implemented');
  }

  focusWindow(windowId, onSuccess, onError) {
    throw new Error('focusWindow is not implemented');
  }

  captureVisible(windowId, tabId, onSuccess, onError) {
    throw new Error('captureVisible is not implemented');
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

  getActiveScreenshot(onSuccess, onError) {
    let queryOptions = { active: true, lastFocusedWindow: true };
    this._browser.tabs.query(queryOptions).then(
      (tabs) => {
        if (!tabs.length) {
          onError('No active tab found');
          return;
        }
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
          (error) => onError(error)
        );
      },
      (error) => onError(error)
    );
  }

  focusWindow(windowId, onSuccess, onError) {
    this._browser.windows.update(windowId, { focused: true }).then(
      onSuccess,
      (error) => onError(error)
    );
  }

  captureVisible(windowId, tabId, onSuccess, onError) {
    this._browser.tabs.captureVisibleTab(windowId, { format: 'png' }).then(
      (data) => onSuccess({
        tab: tabId,
        window: windowId,
        data: data
      }),
      (error) => onError(error)
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

  close(tab_ids, onSuccess, onError) {
    this._browser.tabs.remove(tab_ids, onSuccess);
  }

  closeWindow(windowId, onSuccess, onError) {
    this._browser.windows.remove(windowId, () => {
      const lastError = this._browser.runtime.lastError;
      if (lastError) {
        onError(lastError.message);
      } else {
        onSuccess();
      }
    });
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

  getActiveScreenshot(onSuccess, onError) {
    // this._browser.tabs.captureVisibleTab(null, { format: 'png' }, onSuccess);
    let queryOptions = { active: true, lastFocusedWindow: true };
    this._browser.tabs.query(queryOptions, (tabs) => {
      if (this._browser.runtime.lastError) {
        onError(this._browser.runtime.lastError.message);
        return;
      }
      if (!tabs.length) {
        onError('No active tab found');
        return;
      }
      let tab = tabs[0];
      let windowId = tab.windowId;
      let tabId = tab.id;
      this._browser.tabs.captureVisibleTab(windowId, { format: 'png' }, function(data) {
        if (chrome.runtime.lastError) {
          onError(chrome.runtime.lastError.message);
          return;
        }
        const message = {
          tab: tabId,
          window: windowId,
          data: data
        };
        onSuccess(message);
      });
    });
  }

  focusWindow(windowId, onSuccess, onError) {
    this._browser.windows.update(windowId, { focused: true }, () => {
      if (chrome.runtime.lastError) {
        onError(chrome.runtime.lastError.message);
        return;
      }
      onSuccess();
    });
  }

  captureVisible(windowId, tabId, onSuccess, onError) {
    this._browser.tabs.captureVisibleTab(windowId, { format: 'png' }, function(data) {
      if (chrome.runtime.lastError) {
        onError(chrome.runtime.lastError.message);
        return;
      }
      onSuccess({
        tab: tabId,
        window: windowId,
        data: data
      });
    });
  }

  runScript(tab_id, script, payload, onSuccess, onError) {
    this._browser.scripting.executeScript(
      {
        target: { tabId: tab_id },
        func: (code) => {
          const parseRegexLiteral = (literal) => {
            const match = literal.match(/^\/((?:\\.|[^/])*)\/([a-z]*)$/);
            if (!match) {
              throw new Error(`Unsupported regex literal: ${literal}`);
            }
            return new RegExp(match[1], match[2]);
          };

          const parseStringLiteral = (literal) => JSON.parse(literal);

          const parseReplaceCall = (source) => {
            const match = source.match(/\.replace\((\/(?:\\.|[^/])*\/[a-z]*),\s*("[\s\S]*")\);?$/);
            if (!match) {
              throw new Error(`Unsupported replace script: ${source}`);
            }
            return [parseRegexLiteral(match[1]), parseStringLiteral(match[2])];
          };

          const documentElement = document.documentElement;
          const text = documentElement ? (documentElement.innerText || '') : '';
          const html = documentElement ? (documentElement.innerHTML || '') : '';

          const wordsMatch = code.match(/innerText\.match\((\/(?:\\.|[^/])*\/[a-z]*)\)\]\.sort\(\)\.join\(("[\s\S]*")\);?$/);
          if (wordsMatch) {
            const matchRegex = parseRegexLiteral(wordsMatch[1]);
            const joinWith = parseStringLiteral(wordsMatch[2]);
            const words = text.match(matchRegex) || [];
            return [...new Set(words)].sort().join(joinWith);
          }

          if (code.includes('document.documentElement.innerText.replace(')) {
            const [delimiterRegex, replaceWith] = parseReplaceCall(code);
            return text.replace(delimiterRegex, replaceWith);
          }

          if (code.includes('document.documentElement.innerHTML.replace(')) {
            const [delimiterRegex, replaceWith] = parseReplaceCall(code);
            return html.replace(delimiterRegex, replaceWith);
          }

          if (code.includes("document.querySelectorAll('audio, video')")) {
            const actionMatch = code.match(/const action = "([^"]+)";/);
            if (!actionMatch) {
              throw new Error(`Unsupported media control script: ${code}`);
            }
            const action = actionMatch[1];
            const media = Array.from(document.querySelectorAll('audio, video'));
            let changed = 0;
            for (const element of media) {
              if (action === 'play') {
                const promise = element.play();
                if (promise && promise.catch) {
                  promise.catch(error => console.log('Could not play media element:', error));
                }
                changed += 1;
              } else if (action === 'pause') {
                if (!element.paused) {
                  element.pause();
                  changed += 1;
                }
              }
            }
            return action + "\t" + changed + "\t" + media.length;
          }

          throw new Error(`Unsupported script: ${code}`);
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
    const KEEPALIVE_ALARM = 'brotab-keepalive';

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
  if (typeof chrome !== 'undefined' && chrome.runtime && chrome.tabs) {
    port = chrome.runtime.connectNative(NATIVE_APP_NAME);
    console.log("It's Chrome/Chromium: " + port);
    browserTabs = new ChromeTabs(chrome);
    attachPortListeners();

  } else if (typeof browser !== 'undefined' && browser.runtime && browser.tabs) {
    port = browser.runtime.connectNative(NATIVE_APP_NAME);
    console.log("It's Firefox: " + port);
    browserTabs = new FirefoxTabs(browser);
    attachPortListeners();

  } else {
    console.log("Unknown browser detected");
  }
}

function attachPortListeners() {
  if (!port) {
    return;
  }

  port.onMessage.addListener(handleNativeMessage);
  port.onDisconnect.addListener(handleNativeDisconnect);
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
    // this post is only required to make brotab move command synchronous. mediator
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
  let replied = false;
  const reply = () => {
    if (replied) {
      return;
    }
    replied = true;
    port.postMessage('OK');
  };

  const fallbackTimer = setTimeout(() => {
    console.warn(`closeTabs timed out for ${JSON.stringify(tab_ids)}`);
    reply();
  }, 2000);

  const finish = () => {
    clearTimeout(fallbackTimer);
    reply();
  };

  try {
    browserTabs.list({}, tabs => {
      try {
        const requestedTabIds = new Set(tab_ids);
        const tabsByWindowId = new Map();
        const closeWindowIds = [];
        const closeTabIds = [];

        for (let tab of tabs) {
          if (!tabsByWindowId.has(tab.windowId)) {
            tabsByWindowId.set(tab.windowId, []);
          }
          tabsByWindowId.get(tab.windowId).push(tab);
        }

        for (let [_windowId, windowTabs] of tabsByWindowId.entries()) {
          const matchingTabs = windowTabs.filter(tab => requestedTabIds.has(tab.id));
          if (matchingTabs.length === 0) {
            continue;
          }

          if (matchingTabs.length === windowTabs.length) {
            closeWindowIds.push(windowTabs[0].windowId);
          } else {
            closeTabIds.push(...matchingTabs.map(tab => tab.id));
          }
        }

        const operations = [];
        if (closeTabIds.length > 0) {
          operations.push(new Promise(resolve => {
            browserTabs.close(
              closeTabIds,
              () => {
                const lastError = chrome.runtime.lastError;
                if (lastError) {
                  console.error(`Error removing tabs ${JSON.stringify(closeTabIds)}: ${lastError.message}`);
                }
                resolve();
              },
              error => {
                console.error(`Error removing tabs ${JSON.stringify(closeTabIds)}: ${error}`);
                resolve();
              }
            );
          }));
        }

        for (let windowId of closeWindowIds) {
          operations.push(new Promise(resolve => {
            browserTabs.closeWindow(
              windowId,
              () => resolve(),
              error => {
                console.error(`Error removing window ${windowId}: ${error}`);
                resolve();
              }
            );
          }));
        }

        Promise.all(operations).then(finish);
      } catch (error) {
        console.error(`closeTabs failed while processing tabs ${JSON.stringify(tab_ids)}: ${error}`);
        browserTabs.close(
          tab_ids,
          finish,
          fallbackError => {
            console.error(`Fallback tab close failed for ${JSON.stringify(tab_ids)}: ${fallbackError}`);
            finish();
          }
        );
      }
    });
  } catch (error) {
    console.error(`closeTabs crashed for ${JSON.stringify(tab_ids)}: ${error}`);
    browserTabs.close(
      tab_ids,
      finish,
      fallbackError => {
        console.error(`Fallback tab close failed for ${JSON.stringify(tab_ids)}: ${fallbackError}`);
        finish();
      }
    );
  }
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

function getMediaControlScript(action) {
  return `(() => {
    const action = ${JSON.stringify(action)};
    const media = Array.from(document.querySelectorAll('audio, video'));
    let changed = 0;
    for (const element of media) {
      if (action === 'play') {
        const promise = element.play();
        if (promise && promise.catch) {
          promise.catch(error => console.log('Could not play media element:', error));
        }
        changed += 1;
      } else if (action === 'pause') {
        if (!element.paused) {
          element.pause();
          changed += 1;
        }
      }
    }
    return action + "\\t" + changed + "\\t" + media.length;
  })();`;
}

function mediaControl(window_id, tab_id, action) {
  const script = getMediaControlScript(action);
  browserTabs.runScript(tab_id, script, null,
    (result, _payload) => {
      result = listOr(result, [`${action}\t0\t0`]);
      port.postMessage([`${window_id}.${tab_id}\t${result[0]}`]);
    },
    (error, _payload) => {
      const message = `mediaControl failed: tab_id=${tab_id}, action=${action}, error=${error}`;
      console.error(message);
      port.postMessage({error: message, window_id: window_id, tab_id: tab_id, action: action});
    }
  );
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

function getActiveScreenshot(wait) {
  const capture = () => browserTabs.getActiveScreenshot(
    (data) => port.postMessage(data),
    (error) => port.postMessage({error: `${error}`})
  );

  if (wait > 0) {
    setTimeout(capture, wait * 1000);
  } else {
    capture();
  }
}

function restoreActiveTab(previousTab) {
  if (!previousTab) {
    return;
  }

  browserTabs.activate(previousTab.id, true);
}

function waitForTabActivation(windowId, tabId, onSuccess, onError, attemptsLeft = 10) {
  browserTabs.query({active: true, windowId: windowId}, (activeTabs) => {
    if (activeTabs.length && activeTabs[0].id === tabId) {
      setTimeout(onSuccess, 150);
      return;
    }

    if (attemptsLeft <= 0) {
      onError(`Timed out waiting for tab ${tabId} in window ${windowId} to become active`);
      return;
    }

    setTimeout(
      () => waitForTabActivation(windowId, tabId, onSuccess, onError, attemptsLeft - 1),
      100
    );
  });
}

function getScreenshot(tab_id, wait) {
  if (tab_id == null) {
    getActiveScreenshot(wait);
    return;
  }

  browserTabs.list({}, (tabs) => {
    const targetTab = tabs.find(tab => tab.id === tab_id);
    if (!targetTab) {
      port.postMessage({error: `No tab found for id ${tab_id}`});
      return;
    }

    browserTabs.query({active: true, lastFocusedWindow: true}, (activeTabs) => {
      const previousTab = activeTabs.length ? activeTabs[0] : null;

      browserTabs.focusWindow(
        targetTab.windowId,
        () => browserTabs.update(
          targetTab.id,
          {active: true},
          () => waitForTabActivation(
            targetTab.windowId,
            targetTab.id,
            () => {
              const capture = () => browserTabs.captureVisible(
                targetTab.windowId,
                targetTab.id,
                (data) => {
                  if (previousTab && previousTab.id !== targetTab.id) {
                    restoreActiveTab(previousTab);
                  }
                  port.postMessage(data);
                },
                (error) => {
                  if (previousTab && previousTab.id !== targetTab.id) {
                    restoreActiveTab(previousTab);
                  }
                  port.postMessage({error: `${error}`});
                }
              );
              if (wait > 0) {
                setTimeout(capture, wait * 1000);
              } else {
                capture();
              }
            },
            (error) => {
              if (previousTab && previousTab.id !== targetTab.id) {
                restoreActiveTab(previousTab);
              }
              port.postMessage({error: `${error}`});
            }
          ),
          (error) => port.postMessage({error: `${error}`})
        ),
        (error) => port.postMessage({error: `${error}`})
      );
    });
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

function getTextForTab(tab_id, delimiter_regex, replace_with) {
  browserTabs.list({'discarded': false}, (tabs) => {
    if (tab_id != null) {
      tabs = tabs.filter(tab => tab.id === tab_id);
    }
    getTextOnListSuccess(tabs, delimiter_regex, replace_with);
  });
}

function getText(delimiter_regex, replace_with) {
  getTextForTab(null, delimiter_regex, replace_with);
}

function getHtmlOnListSuccess(tabs, delimiter_regex, replace_with) {
  // Make sure tabs are sorted by their index within a window
  tabs.sort(compareWindowIdTabId);
  getTextOrHtmlFromTabs(tabs, getHtmlScript, delimiter_regex, replace_with, getTextOnRunScriptSuccess);
}

function getHtmlForTab(tab_id, delimiter_regex, replace_with) {
  browserTabs.list({'discarded': false}, (tabs) => {
    if (tab_id != null) {
      tabs = tabs.filter(tab => tab.id === tab_id);
    }
    getHtmlOnListSuccess(tabs, delimiter_regex, replace_with);
  });
}

function getHtml(delimiter_regex, replace_with) {
  getHtmlForTab(null, delimiter_regex, replace_with);
}

function getBrowserName() {
  const name = browserTabs.getBrowserName();
  console.log("Sending browser name: " + name);
  port.postMessage(name);
}

/*
Listen for messages from the app.
*/
function handleNativeMessage(command) {
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

  else if (command['name'] == 'media_control') {
    console.log('Controlling media:', command['window_id'], command['tab_id'], command['action']);
    mediaControl(command['window_id'], command['tab_id'], command['action']);
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
    getScreenshot(command['tab_id'], command['wait']);
  }

  else if (command['name'] == 'get_words') {
    console.log('Getting words from tab:', command['tab_id']);
    getWords(command['tab_id'], command['match_regex'], command['join_with']);
  }

  else if (command['name'] == 'get_text') {
    console.log('Getting texts from all tabs');
    getTextForTab(command['tab_id'], command['delimiter_regex'], command['replace_with']);
  }

  else if (command['name'] == 'get_html') {
    console.log('Getting HTML from all tabs');
    getHtmlForTab(command['tab_id'], command['delimiter_regex'], command['replace_with']);
  }

  else if (command['name'] == 'get_browser') {
    console.log('Getting browser name');
    getBrowserName();
  }

  else {
    const error = `Unknown command: ${command['name']}`;
    console.warn(error);
    port.postMessage({error: error});
  }
}

function handleNativeDisconnect() {
  console.log("Disconnected");
  if(chrome.runtime.lastError) {
    console.warn("Reason: " + chrome.runtime.lastError.message);
  } else {
    console.warn("lastError is undefined");
  }
  //sleep(5000);
  console.log("Trying to reconnect");
  reconnect();
}

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
