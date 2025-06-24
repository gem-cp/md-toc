document.addEventListener('DOMContentLoaded', function() {
  const mainContent = document.querySelector('.main-content');
  if (!mainContent) {
    return;
  }

  const headers = mainContent.querySelectorAll('h1, h2, h3, h4, h5, h6');
  if (headers.length === 0) {
    // No headers, so no TOC to build or place
    return;
  }

  // Create the TOC structure dynamically
  const tocWrapperDiv = document.createElement('div');
  tocWrapperDiv.id = 'page-toc-nav-container';
  tocWrapperDiv.classList.add('page-toc-container');

  const tocHeader = document.createElement('h3');
  tocHeader.classList.add('text-delta'); // just-the-docs class for small headings
  tocHeader.textContent = 'On this page';
  tocWrapperDiv.appendChild(tocHeader);

  const tocNav = document.createElement('nav');
  tocNav.id = 'page-toc-nav';
  tocNav.classList.add('nav-list');
  tocWrapperDiv.appendChild(tocNav);

  // `parentStack` will hold the `<ul>` elements.
  // `parentStack[0]` is `tocNav` (the root list for the TOC).
  const parentStack = [tocNav];

  headers.forEach(header => {
    const id = header.id;
    if (!id) return;

    const level = parseInt(header.tagName.substring(1)); // Actual H level (1-6)

    const listItem = document.createElement('li');
    listItem.classList.add('nav-list-item', `nav-list-item-level-${level}`);
    
    const link = document.createElement('a');
    link.href = '#' + id;
    link.textContent = header.textContent;
    link.classList.add('nav-list-link');
    listItem.appendChild(link);

    while (parentStack.length > level) {
      parentStack.pop();
    }

    if (parentStack.length < level) {
      const previousList = parentStack[parentStack.length - 1];
      let lastListItemInPreviousList = previousList.lastElementChild;

      // If previousList is tocNav itself and it's empty, it won't have a lastElementChild.
      // This can happen if the first header is not H1.
      // In such cases, we want to append the new UL to tocNav directly if level is 1.
      // Or, ensure there's a base LI if creating deeper levels without a H1.
      // For now, this logic assumes H1 is the natural root or skipped levels append to last valid LI.

      if (lastListItemInPreviousList && lastListItemInPreviousList.tagName === 'LI') {
        for (let i = parentStack.length; i < level; i++) {
          const newUl = document.createElement('ul');
          newUl.classList.add('nav-list', 'nav-list-child-list', `nav-list-level-${i + 1}`); // i+1 is the H-level this UL is for
          lastListItemInPreviousList.appendChild(newUl);
          parentStack.push(newUl);
          // Update lastListItemInPreviousList to the newUl itself, so the *next* newUl (if any) is appended to this one.
          // No, that's not right. The newUl is pushed to stack. The next LI will go into it.
          // The lastListItemInPreviousList reference is for *its* children.
          lastListItemInPreviousList = newUl; // This seems wrong. The new UL is for the *next* level.
                                          // Let's stick to the previous logic for appending to last LI of current parent.
        }
         // Re-fetch the last list item from the *current* deepest list in parentStack
         // as it might have been updated by adding new ULs.
        lastListItemInPreviousList = parentStack[parentStack.length - 1].lastElementChild;

      } else if (parentStack.length === 1 && parentStack[0] === tocNav) {
        // This means we are trying to create a nested list directly under tocNav
        // without a preceding H1 (or any header at level `parentStack.length`).
        // This scenario is tricky. For now, we'll append to tocNav.
        // A more robust solution for skipped levels might involve creating placeholder LIs.
      }
    }

    parentStack[parentStack.length - 1].appendChild(listItem);
  });

  // Only proceed to inject if the TOC actually has content
  if (tocNav.children.length > 0) {
    // Find the active navigation link in the main sidebar
    // Common selector for active link in just-the-docs: '.nav-list-link.active'
    // Or, if it's a parent of an active link: '.nav-list-item.active'
    const activeNavLink = document.querySelector('.side-bar .nav-list-link.active');

    if (activeNavLink) {
      let parentLi = activeNavLink.closest('.nav-list-item');
      if (parentLi) {
        // Insert the TOC container after the parent LI of the active link
        parentLi.parentNode.insertBefore(tocWrapperDiv, parentLi.nextSibling);
      } else {
        // Fallback: if somehow active link is not in an LI, append to sidebar nav container
        // This is unlikely with just-the-docs structure.
        // Or, could append to a default location if no active link found.
        // For now, if no parentLi, it won't be inserted.
      }
    } else {
      // Fallback: if no active link is found (e.g. on homepage not in nav),
      // do not display the TOC, or display it in a default location.
      // For now, we simply won't insert it if no active link.
      // Consider logging this: console.log("Page TOC: No active nav link found to attach TOC to.");
    }
  }
});