// Menu functionality
frappe.provide('onhire_pro.menu');

onhire_pro.menu = {
  init: function() {
    this.setupMobileMenu();
    this.setupDropdowns();
    this.setupActiveLinks();
    this.setupSmoothScroll();
    this.setupNestedMenus();
    this.setupKeyboardNavigation(); // Added keyboard navigation
    this.setupSearchFilter(); // Added search functionality
    this.setupMenuGroups(); // Added menu grouping
    this.setupTooltips(); // Added tooltips
    this.setupMenuState(); // Added menu state persistence
  },

  // New: Setup keyboard navigation
  setupKeyboardNavigation: function() {
    const menuItems = document.querySelectorAll('.menu-item, .dropdown-item');
    
    menuItems.forEach(item => {
      item.addEventListener('keydown', (e) => {
        switch(e.key) {
          case 'ArrowDown':
            e.preventDefault();
            this.focusNextItem(item);
            break;
          case 'ArrowUp':
            e.preventDefault();
            this.focusPreviousItem(item);
            break;
          case 'Enter':
          case ' ':
            e.preventDefault();
            item.click();
            break;
        }
      });
    });
  },

  focusNextItem: function(currentItem) {
    const items = Array.from(currentItem.parentElement.children);
    const currentIndex = items.indexOf(currentItem);
    const nextItem = items[currentIndex + 1] || items[0];
    nextItem?.focus();
  },

  focusPreviousItem: function(currentItem) {
    const items = Array.from(currentItem.parentElement.children);
    const currentIndex = items.indexOf(currentItem);
    const previousItem = items[currentIndex - 1] || items[items.length - 1];
    previousItem?.focus();
  },

  // New: Setup search filter for menus
  setupSearchFilter: function() {
    const menuContainers = document.querySelectorAll('.sidebar-menu, .dropdown-menu');
    
    menuContainers.forEach(container => {
      const searchInput = document.createElement('input');
      searchInput.type = 'text';
      searchInput.className = 'menu-search';
      searchInput.placeholder = 'Search menu...';
      
      searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const menuItems = container.querySelectorAll('.menu-item, .dropdown-item');
        
        menuItems.forEach(item => {
          const text = item.textContent.toLowerCase();
          item.style.display = text.includes(searchTerm) ? '' : 'none';
        });
      });
      
      container.insertBefore(searchInput, container.firstChild);
    });
  },

  // New: Setup menu groups
  setupMenuGroups: function() {
    const menuGroups = document.querySelectorAll('.menu-group');
    
    menuGroups.forEach(group => {
      const header = group.querySelector('.menu-group-header');
      const content = group.querySelector('.menu-group-content');
      
      if (header && content) {
        header.addEventListener('click', () => {
          const isExpanded = content.classList.contains('expanded');
          
          // Close other groups
          document.querySelectorAll('.menu-group-content.expanded').forEach(item => {
            if (item !== content) {
              item.classList.remove('expanded');
              item.style.maxHeight = '0px';
            }
          });
          
          // Toggle current group
          content.classList.toggle('expanded');
          content.style.maxHeight = isExpanded ? '0px' : `${content.scrollHeight}px`;
        });
      }
    });
  },

  // New: Setup tooltips
  setupTooltips: function() {
    const menuItems = document.querySelectorAll('[data-tooltip]');
    
    menuItems.forEach(item => {
      const tooltip = document.createElement('div');
      tooltip.className = 'menu-tooltip';
      tooltip.textContent = item.getAttribute('data-tooltip');
      
      item.addEventListener('mouseenter', () => {
        document.body.appendChild(tooltip);
        const rect = item.getBoundingClientRect();
        tooltip.style.top = `${rect.bottom + 5}px`;
        tooltip.style.left = `${rect.left}px`;
      });
      
      item.addEventListener('mouseleave', () => {
        tooltip.remove();
      });
    });
  },

  // New: Setup menu state persistence
  setupMenuState: function() {
    // Restore menu state
    const savedState = localStorage.getItem('menuState');
    if (savedState) {
      const state = JSON.parse(savedState);
      state.expandedGroups?.forEach(groupId => {
        const group = document.getElementById(groupId);
        if (group) {
          const content = group.querySelector('.menu-group-content');
          content?.classList.add('expanded');
        }
      });
    }

    // Save menu state on changes
    document.querySelectorAll('.menu-group').forEach(group => {
      group.addEventListener('click', () => {
        const expandedGroups = Array.from(document.querySelectorAll('.menu-group-content.expanded'))
          .map(content => content.parentElement.id);
        localStorage.setItem('menuState', JSON.stringify({ expandedGroups }));
      });
    });
  },

  // Rest of the existing methods...
};
