// Displays a status message with the provided text and appropriate background color
function showStatusMessage(message, isError) {
  var status = document.getElementById('status');
  status.textContent = message;
  
  status.style.backgroundColor = isError ? '#FFC0C0' : '#C0FFC0'; // Light red or light green
  status.style.padding = '10px';
  
  var closeButton = document.createElement('button');
  closeButton.innerHTML = '\u2715'; // ✕ symbol (Unicode)
  closeButton.style.marginLeft = '10px';
  closeButton.style.border = 'none';
  closeButton.style.backgroundColor = 'transparent';
  closeButton.style.cursor = 'pointer';
  
  closeButton.addEventListener('click', function() {
    status.textContent = '';
    status.style.backgroundColor = 'transparent';
  });

  status.appendChild(closeButton);
}



// Saves options to chrome.storage
function save_options() {
  var newIdentifier = document.getElementById('instanceInput').value.trim();

  // Check for valid characters (alphanumeric + "_" + ".")
  var validCharacters = /^[a-zA-Z0-9_.]+$/;
  if (!validCharacters.test(newIdentifier)) {
    showStatusMessage('Invalid characters. Only alphanumeric, "_" and "." are allowed.', true);
    return;
  }

  // Check maximum length
  if (newIdentifier.length > 128) {
    showStatusMessage('Value is too long. Maximum length is 128 characters.', true);
    return;
  }

  chrome.storage.sync.set({
    instanceIdentifier: newIdentifier
  }, function() {
    showStatusMessage('Options saved.', false);
  });
}

// Restores text input using the preferences
// stored in chrome.storage.
function restore_options() {
  // Use default value '[none]'.
  chrome.storage.sync.get({
    instanceIdentifier: '[none]'
  }, function(items) {
    document.getElementById('instanceInput').value = items.instanceIdentifier;
  });
}

document.addEventListener('DOMContentLoaded', restore_options);
document.getElementById('optionsForm').addEventListener('submit', function(e) {
  e.preventDefault();
  save_options();
});
