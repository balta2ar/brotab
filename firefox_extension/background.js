/*
On startup, connect to the "firefox_mediator" app.
*/
var port = browser.runtime.connectNative("firefox_mediator");

function listTabsSuccess(tabs) {
  lines = [];
  for (let tab of tabs) {
    line = tab.id + "\t" + tab.title;
    console.log(line);
    lines.push(line);
  }
  port.postMessage(lines);
}

function listTabsError(error) {
  console.log(`Error: ${error}`);
}

function listTabs() {
  var querying = browser.tabs.query({});
  querying.then(listTabsSuccess, listTabsError);
}

function closeTabs(tab_ids) {
  browser.tabs.remove(tab_ids);
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
  
  else if (command['name'] == 'new_tab') {
    console.log('Creating tab:', command['url']);
    createTab(command['url']);
  }

  else if (command['name'] == 'activate_tab') {
    console.log('Activating tab:', command['tab_id']);
    activateTab(command['tab_id']);
  }
});

/*
On a click on the browser action, send the app a message.
*/
browser.browserAction.onClicked.addListener(() => {
  // console.log("Sending:  ping");
  // port.postMessage("ping");

  console.log('Listing tabs');
  listTabs();
});
