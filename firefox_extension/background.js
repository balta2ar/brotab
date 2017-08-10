/*
On startup, connect to the "firefox_mediator" app.
*/
var port = browser.runtime.connectNative("firefox_mediator");

function listTabsSuccess(tabs) {
  for (let tab of tabs) {
    console.log(tab.id + ", " + tab.title);
  }
}

function listTabsError(error) {
  console.log(`Error: ${error}`);
}

function listTabs() {
  var querying = browser.tabs.query({});
  querying.then(listTabsSuccess, listTabsError);
}

/*
Listen for messages from the app.
*/
port.onMessage.addListener((response) => {
  console.log("Received: " + response);
});

/*
On a click on the browser action, send the app a message.
*/
browser.browserAction.onClicked.addListener(() => {
  // console.log("Sending:  ping");
  // port.postMessage("ping");

  console.log('Listing tabs')
  listTabs()
});
