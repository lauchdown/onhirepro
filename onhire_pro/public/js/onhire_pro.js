// OnHire Pro Main JavaScript
frappe.provide('onhire_pro');

onhire_pro.init = function() {
  // Initialize modern UI components
  this.initializeUI();
  
  // Setup global event handlers
  this.setupEventHandlers();
  
  // Initialize any required plugins
  this.initializePlugins();
};

onhire_pro.initializeUI = function() {
  // Add modern styling to all pages
  this.applyModernStyling();
  
  // Initialize responsive navigation
  this.initializeNavigation();
  
  // Setup theme preferences
  this.setupThemePreferences();
};

onhire_pro.applyModernStyling = function() {
  // Add modern classes to existing elements
  $('.page-container').addClass('modern-container');
  $('.form-section').addClass('modern-form-section');
  $('.list-row').addClass('modern-list-row');
  
  // Enhance buttons
  $('button, .btn').each(function() {
    if (!$(this).hasClass('btn-modern')) {
      $(this).addClass('btn-modern');
    }
  });
  
  // Enhance form inputs
  $('input, select, textarea').each(function() {
    if (!$(this).hasClass('modern-input')) {
      $(this).addClass('modern-input');
    }
  });
};

onhire_pro.initializeNavigation = function() {
  // Add smooth scrolling
  $('a[href*="#"]').not('[href="#"]').click(function(event) {
    if (
      location.pathname.replace(/^\//, '') == this.pathname.replace(/^\//, '') 
      && 
      location.hostname == this.hostname
    ) {
      let target = $(this.hash);
      target = target.length ? target : $('[name=' + this.hash.slice(1) + ']');
      if (target.length) {
        event.preventDefault();
        $('html, body').animate({
          scrollTop: target.offset().top - 100
        }, 1000);
      }
    }
  });
  
  // Responsive navigation toggle
  $('.nav-toggle').click(function() {
    $('.nav-menu').toggleClass('active');
  });
};

onhire_pro.setupThemePreferences = function() {
  // Check for saved theme preference
  const savedTheme = localStorage.getItem('onhire_pro_theme');
  if (savedTheme) {
    document.body.setAttribute('data-theme', savedTheme);
  }
  
  // Theme toggle functionality
  $('.theme-toggle').click(function() {
    const currentTheme = document.body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('onhire_pro_theme', newTheme);
  });
};

onhire_pro.setupEventHandlers = function() {
  // Global form submission handler
  $(document).on('submit', 'form', function(e) {
    const $form = $(this);
    if (!$form.hasClass('no-loading-state')) {
      $form.addClass('loading');
    }
  });
  
  // Global ajax error handler
  $(document).ajaxError(function(event, jqXHR, settings, error) {
    frappe.show_alert({
      message: __('An error occurred. Please try again.'),
      indicator: 'red'
    });
  });
  
  // Responsive table handling
  $(window).on('resize', function() {
    $('.table-container').each(function() {
      const $container = $(this);
      const $table = $container.find('table');
      if ($table.width() > $container.width()) {
        $container.addClass('table-scroll');
      } else {
        $container.removeClass('table-scroll');
      }
    });
  }).trigger('resize');
};

onhire_pro.initializePlugins = function() {
  // Initialize any third-party plugins
  this.initializeTooltips();
  this.initializeDatePickers();
  this.initializeSelect2();
};

onhire_pro.initializeTooltips = function() {
  $('[data-toggle="tooltip"]').tooltip({
    template: `
      <div class="tooltip modern-tooltip" role="tooltip">
        <div class="tooltip-arrow"></div>
        <div class="tooltip-inner"></div>
      </div>
    `
  });
};

onhire_pro.initializeDatePickers = function() {
  $('.datepicker').each(function() {
    $(this).datepicker({
      autoclose: true,
      todayHighlight: true,
      template: `
        <div class="datepicker modern-datepicker">
          <div class="datepicker-days">
            <table class="table-condensed">
              <thead>
                <tr>
                  <th class="prev">‹</th>
                  <th colspan="5" class="datepicker-switch"></th>
                  <th class="next">›</th>
                </tr>
                <tr>
                  <th class="dow"></th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      `
    });
  });
};

onhire_pro.initializeSelect2 = function() {
  $('.select2').select2({
    theme: 'modern',
    dropdownAutoWidth: true,
    width: '100%'
  });
};

// Initialize OnHire Pro
$(document).ready(function() {
  onhire_pro.init();
});
