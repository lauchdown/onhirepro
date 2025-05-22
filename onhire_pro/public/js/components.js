// Modern UI Components
frappe.provide('onhire_pro.ui');

onhire_pro.ui = {
  // Create a modern card component
  createCard: function(options) {
    const card = document.createElement('div');
    card.className = `card ${options.className || ''}`;
    
    if (options.header) {
      const header = document.createElement('div');
      header.className = 'card-header flex justify-between items-center';
      header.innerHTML = `
        <h3>${options.header}</h3>
        ${options.headerActions || ''}
      `;
      card.appendChild(header);
    }
    
    const body = document.createElement('div');
    body.className = 'card-body';
    body.innerHTML = options.content;
    card.appendChild(body);
    
    if (options.footer) {
      const footer = document.createElement('div');
      footer.className = 'card-footer';
      footer.innerHTML = options.footer;
      card.appendChild(footer);
    }
    
    return card;
  },
  
  // Create a modern data table
  createDataTable: function(options) {
    const tableContainer = document.createElement('div');
    tableContainer.className = 'table-container';
    
    const table = document.createElement('table');
    table.className = 'table';
    
    // Create header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    options.columns.forEach(column => {
      const th = document.createElement('th');
      th.textContent = column.label;
      if (column.width) th.style.width = column.width;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Create body
    const tbody = document.createElement('tbody');
    options.data.forEach(row => {
      const tr = document.createElement('tr');
      options.columns.forEach(column => {
        const td = document.createElement('td');
        td.innerHTML = row[column.field] || '';
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    
    tableContainer.appendChild(table);
    return tableContainer;
  },
  
  // Create a modern form group
  createFormGroup: function(options) {
    const formGroup = document.createElement('div');
    formGroup.className = 'form-group';
    
    if (options.label) {
      const label = document.createElement('label');
      label.className = 'form-label';
      label.htmlFor = options.id;
      label.textContent = options.label;
      formGroup.appendChild(label);
    }
    
    const input = document.createElement(options.type === 'textarea' ? 'textarea' : 'input');
    input.className = 'form-control';
    input.id = options.id;
    input.name = options.name || options.id;
    if (options.type !== 'textarea') input.type = options.type || 'text';
    if (options.placeholder) input.placeholder = options.placeholder;
    if (options.value) input.value = options.value;
    if (options.required) input.required = true;
    
    formGroup.appendChild(input);
    
    if (options.helpText) {
      const help = document.createElement('small');
      help.className = 'form-help-text';
      help.textContent = options.helpText;
      formGroup.appendChild(help);
    }
    
    return formGroup;
  },
  
  // Create a modern alert component
  createAlert: function(options) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${options.type || 'info'} fade-in`;
    
    alert.innerHTML = `
      <div class="alert-icon">
        ${options.icon || ''}
      </div>
      <div class="alert-content">
        ${options.title ? `<h4 class="alert-title">${options.title}</h4>` : ''}
        <p class="alert-message">${options.message}</p>
      </div>
      ${options.dismissible ? '<button class="alert-close">&times;</button>' : ''}
    `;
    
    if (options.dismissible) {
      alert.querySelector('.alert-close').addEventListener('click', () => {
        alert.remove();
      });
    }
    
    if (options.autoClose) {
      setTimeout(() => {
        alert.remove();
      }, options.autoClose);
    }
    
    return alert;
  },
  
  // Create a modern badge component
  createBadge: function(options) {
    const badge = document.createElement('span');
    badge.className = `badge badge-${options.type || 'default'}`;
    badge.textContent = options.text;
    return badge;
  },
  
  // Create a modern button component
  createButton: function(options) {
    const button = document.createElement('button');
    button.className = `btn btn-${options.type || 'primary'} ${options.className || ''}`;
    button.type = options.submit ? 'submit' : 'button';
    
    if (options.icon) {
      button.innerHTML = `
        <span class="btn-icon">${options.icon}</span>
        <span class="btn-text">${options.text}</span>
      `;
    } else {
      button.textContent = options.text;
    }
    
    if (options.onClick) {
      button.addEventListener('click', options.onClick);
    }
    
    return button;
  },
  
  // Create a modern loading spinner
  createSpinner: function(options = {}) {
    const spinner = document.createElement('div');
    spinner.className = `spinner ${options.className || ''}`;
    return spinner;
  },
  
  // Create a modern modal dialog
  createModal: function(options) {
    const modal = document.createElement('div');
    modal.className = 'modal fade-in';
    
    modal.innerHTML = `
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h4 class="modal-title">${options.title}</h4>
            <button type="button" class="modal-close">&times;</button>
          </div>
          <div class="modal-body">
            ${options.content}
          </div>
          ${options.footer ? `
            <div class="modal-footer">
              ${options.footer}
            </div>
          ` : ''}
        </div>
      </div>
    `;
    
    // Close modal functionality
    const closeModal = () => {
      modal.classList.add('fade-out');
      setTimeout(() => modal.remove(), 200);
    };
    
    modal.querySelector('.modal-close').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
    
    return modal;
  }
};
