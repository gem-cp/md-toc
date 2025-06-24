document.addEventListener('DOMContentLoaded', function() {
  const tocContainer = document.getElementById('page-toc-nav');
  // Der Hauptinhaltsbereich in "Just the Docs" hat die Klasse .main-content
  const mainContent = document.querySelector('.main-content'); 

  if (!tocContainer || !mainContent) {
    return;
  }

  // Find all H2 and H3 headers within the main content area
  const headers = mainContent.querySelectorAll('h2, h3');
  
  // Clear the "Wird geladen..." message
  tocContainer.innerHTML = '';

  if (headers.length === 0) {
    // If no headers, hide the entire "Auf dieser Seite" block
    const container = document.querySelector('.js-page-toc-container');
    if (container) {
      container.style.display = 'none';
    }
    return;
  }

  let lastH2ListItem = null;
  let sublist = null;

  headers.forEach(header => {
    const id = header.id;
    if (!id) return; // Skip headers without an ID

    const listItem = document.createElement('li');
    const link = document.createElement('a');
    
    link.href = '#' + id;
    link.textContent = header.textContent;
    link.classList.add('nav-list-link');
    listItem.appendChild(link);

    if (header.tagName === 'H2') {
      listItem.classList.add('nav-list-item');
      tocContainer.appendChild(listItem);
      lastH2ListItem = listItem;
      sublist = null; // Reset sublist for the new H2
    } else if (header.tagName === 'H3' && lastH2ListItem) {
      // If a sublist doesn't exist for the current H2, create it
      if (!sublist) {
        sublist = document.createElement('ul');
        sublist.classList.add('nav-list', 'nav-list-child-list');
        lastH2ListItem.appendChild(sublist);
      }
      listItem.classList.add('nav-list-item');
      sublist.appendChild(listItem);
    }
  });
});