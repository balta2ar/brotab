// Saves options to chrome.storage
function save_options() {
  var instanceIdentifier = document.getElementById('instanceIdentifier').value;
  chrome.storage.sync.set({
    instanceIdentifier: instanceIdentifier
  }, function() {
    // Update status to let user know options were saved.
    var status = document.getElementById('status');
    status.textContent = 'Options saved.';
    setTimeout(function() {
      status.textContent = '';
    }, 750);
  });
}

// Restores select box using the preferences
// stored in chrome.storage.
function restore_options() {
  // Use default value color = 'red' and likesColor = true.
  chrome.storage.sync.get({
    instanceIdentifier: '[none]'
  }, function(items) {
    document.getElementById('instanceIdentifier').value = items.instanceIdentifier;
  });
}
document.addEventListener('DOMContentLoaded', restore_options);
document.getElementById('save').addEventListener('click',
    save_options);
