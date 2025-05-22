// RentalHub Portal JavaScript
$(document).ready(function() {
    // Initialize tooltips
    $('[data-toggle="tooltip"]').tooltip();
    
    // Add active class to current navigation item
    const currentPath = window.location.pathname;
    $('.rentalhub-nav .nav-link').each(function() {
        const linkPath = $(this).attr('href');
        if (currentPath.includes(linkPath) && linkPath !== '/') {
            $(this).addClass('active');
        }
    });
    
    // Enhanced date picker functionality
    if ($('#start-date').length && $('#end-date').length) {
        // Initialize date pickers with today as minimum date
        const today = new Date().toISOString().split('T')[0];
        $("#start-date").attr('min', today);
        $("#end-date").attr('min', today);
        
        // Set end date min value when start date changes
        $("#start-date").change(function() {
            const startDate = $(this).val();
            $("#end-date").attr('min', startDate);
            
            // If end date is before start date, update it
            if($("#end-date").val() && $("#end-date").val() < startDate) {
                $("#end-date").val(startDate);
            }
            
            // Calculate rental duration
            updateRentalDuration();
        });
        
        // Update duration when end date changes
        $("#end-date").change(function() {
            updateRentalDuration();
        });
    }
    
    // Function to calculate and display rental duration
    function updateRentalDuration() {
        if ($('#rental-duration').length && $('#start-date').val() && $('#end-date').val()) {
            const startDate = new Date($('#start-date').val());
            const endDate = new Date($('#end-date').val());
            const diffTime = Math.abs(endDate - startDate);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1; // Include both start and end days
            
            $('#rental-duration').text(diffDays + ' days');
            
            // Update pricing if available
            updatePricing(diffDays);
        }
    }
    
    // Function to update pricing based on duration
    function updatePricing(days) {
        if ($('.pricing-display').length) {
            // Get rates from data attributes
            const dailyRate = parseFloat($('.pricing-display').data('daily-rate'));
            const weeklyRate = parseFloat($('.pricing-display').data('weekly-rate'));
            const monthlyRate = parseFloat($('.pricing-display').data('monthly-rate'));
            
            let totalPrice = 0;
            let pricingType = '';
            
            // Calculate best pricing option
            if (days >= 30 && monthlyRate) {
                const months = Math.floor(days / 30);
                const remainingDays = days % 30;
                totalPrice = (months * monthlyRate) + (remainingDays * dailyRate);
                pricingType = months + ' month(s) + ' + remainingDays + ' day(s)';
            } else if (days >= 7 && weeklyRate) {
                const weeks = Math.floor(days / 7);
                const remainingDays = days % 7;
                totalPrice = (weeks * weeklyRate) + (remainingDays * dailyRate);
                pricingType = weeks + ' week(s) + ' + remainingDays + ' day(s)';
            } else {
                totalPrice = days * dailyRate;
                pricingType = days + ' day(s)';
            }
            
            // Update display
            $('.pricing-display .total-price').text('$' + totalPrice.toFixed(2));
            $('.pricing-display .pricing-type').text(pricingType);
        }
    }
    
    // Enhanced client-side search filtering
    $("#search").on("keyup", function() {
        const value = $(this).val().toLowerCase();
        $(".item-card").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
        });
        
        // Show no results message if all items are filtered out
        if($(".item-card:visible").length === 0) {
            if($("#no-results-message").length === 0) {
                $("#items-container").append('<div id="no-results-message" class="col-12"><div class="alert alert-info"><i class="fa fa-info-circle me-2"></i> No equipment found matching your search. Please try different keywords.</div></div>');
            }
        } else {
            $("#no-results-message").remove();
        }
    });
    
    // Category filtering with animation
    $("#category").change(function() {
        const category = $(this).val();
        $(".item-card").hide().removeClass("show");
        
        if(category) {
            $(".item-card[data-category='" + category + "']").show().addClass("show");
        } else {
            $(".item-card").show().addClass("show");
        }
        
        // Show no results message if all items are filtered out
        if($(".item-card:visible").length === 0) {
            if($("#no-results-message").length === 0) {
                $("#items-container").append('<div id="no-results-message" class="col-12"><div class="alert alert-info"><i class="fa fa-info-circle me-2"></i> No equipment found in this category. Please try a different category.</div></div>');
            }
        } else {
            $("#no-results-message").remove();
        }
    });
    
    // Thumbnail image click handler for item detail page
    $(".thumbnail-image").click(function() {
        const imgSrc = $(this).attr('src');
        $(".item-image-container img:first").attr('src', imgSrc);
    });
    
    // Availability check form submission
    $("#availability-form").submit(function(e) {
        e.preventDefault();
        const startDate = $("#check-start-date").val();
        const endDate = $("#check-end-date").val();
        
        // Show loading indicator
        $("#availability-result").html('<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>').show();
        
        // Make AJAX call to check availability
        $.ajax({
            url: '/api/method/onhire_pro.api.check_item_availability',
            type: 'POST',
            data: {
                item_code: $('#availability-form').data('item-code'),
                start_date: startDate,
                end_date: endDate
            },
            success: function(data) {
                if(data.message.available) {
                    $("#availability-result").html('<div class="alert alert-success"><i class="fa fa-check-circle me-2"></i> This item is available for your selected dates!</div>');
                    $(".booking-actions .btn-primary").prop('disabled', false).attr('href', '/rental-booking-request?item=' + $('#availability-form').data('item-code') + '&start_date=' + startDate + '&end_date=' + endDate);
                } else {
                    $("#availability-result").html('<div class="alert alert-danger"><i class="fa fa-times-circle me-2"></i> Sorry, this item is not available for your selected dates.</div>');
                    $(".booking-actions .btn-primary").prop('disabled', true);
                }
            },
            error: function() {
                $("#availability-result").html('<div class="alert alert-danger"><i class="fa fa-exclamation-circle me-2"></i> Error checking availability. Please try again.</div>');
            }
        });
    });
    
    // Mobile navigation toggle
    $(".mobile-nav-toggle").click(function() {
        $(".rentalhub-nav").toggleClass("show");
    });
});
