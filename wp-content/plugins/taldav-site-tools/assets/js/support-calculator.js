(function () {
    'use strict';

    function numberFromData(element, name, fallback) {
        var value = Number(element.getAttribute(name));
        return Number.isFinite(value) ? value : fallback;
    }

    function money(value, currency) {
        return currency + Math.round(value).toLocaleString('en-US');
    }

    function getModal() {
        return document.getElementById('taldav-support-calculator');
    }

    function dispatchFieldEvents(field) {
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function getFieldRoot(modal) {
        var selector = modal.getAttribute('data-form-selector');

        if (!selector) {
            return document;
        }

        try {
            return document.querySelector(selector) || document;
        } catch (error) {
            console.warn('TalDav Site Tools: invalid form selector', selector);
            return document;
        }
    }

    function findField(modal, fieldName) {
        var root = getFieldRoot(modal);

        if (!fieldName) {
            return null;
        }

        return Array.prototype.slice.call(root.querySelectorAll('[name]')).find(function (field) {
            return field.getAttribute('name') === fieldName;
        }) || null;
    }

    function updateSelectedStyles(modal) {
        modal.querySelectorAll('.taldav-calculator-option').forEach(function (option) {
            var input = option.querySelector('input[data-price]');
            option.classList.toggle('is-selected', Boolean(input && input.checked));
        });
    }

    function selectedInputs(modal) {
        return Array.prototype.slice.call(modal.querySelectorAll('input[data-price]:checked'));
    }

    function calculate(modal) {
        var currency = modal.getAttribute('data-currency') || '$';
        var discountEnabled = modal.getAttribute('data-discount-enabled') === '1';
        var discountMinTotal = numberFromData(modal, 'data-discount-min-total', 0);
        var discountPercent = numberFromData(modal, 'data-discount-percent', 0);
        var checked = selectedInputs(modal);
        var subtotal = checked.reduce(function (sum, input) {
            return sum + Number(input.getAttribute('data-price') || 0);
        }, 0);
        var discount = discountEnabled && subtotal >= discountMinTotal ? subtotal * discountPercent / 100 : 0;
        var total = Math.max(0, subtotal - discount);
        var labels = checked.map(function (input) {
            return input.getAttribute('data-label') + ' (' + money(Number(input.getAttribute('data-price') || 0), currency) + ')';
        });

        return {
            currency: currency,
            labels: labels,
            subtotal: subtotal,
            discount: discount,
            total: total,
            summary: labels.join(', ')
        };
    }

    function updateCalculator(modal) {
        var result = calculate(modal);
        var totalNode = modal.querySelector('[data-taldav-total]');
        var discountRow = modal.querySelector('[data-taldav-discount-row]');
        var discountNode = modal.querySelector('[data-taldav-discount]');

        if (totalNode) {
            totalNode.textContent = money(result.total, result.currency) + '/month';
        }

        if (discountRow && discountNode) {
            discountRow.hidden = result.discount <= 0;
            discountNode.textContent = '-' + money(result.discount, result.currency);
        }

        updateSelectedStyles(modal);
    }

    function openCalculator() {
        var modal = getModal();

        if (!modal) {
            return;
        }

        modal.hidden = false;
        document.documentElement.classList.add('taldav-calculator-open');
        updateCalculator(modal);
    }

    function closeCalculator() {
        var modal = getModal();

        if (!modal) {
            return;
        }

        modal.hidden = true;
        document.documentElement.classList.remove('taldav-calculator-open');
    }

    function applyEstimate() {
        var modal = getModal();

        if (!modal) {
            return;
        }

        var result = calculate(modal);
        var priceFieldName = modal.getAttribute('data-price-field-name') || 'estimated_monthly_price';
        var servicesFieldName = modal.getAttribute('data-services-field-name') || 'selected_custom_services';
        var priceField = findField(modal, priceFieldName);
        var servicesField = findField(modal, servicesFieldName);

        if (priceField) {
            priceField.value = money(result.total, result.currency) + '/month';
            dispatchFieldEvents(priceField);
        }

        if (servicesField) {
            servicesField.value = result.summary;
            dispatchFieldEvents(servicesField);
        }

        closeCalculator();
    }

    function isCalculatorLink(element) {
        if (!element || element.tagName !== 'A') {
            return false;
        }

        var href = element.getAttribute('href');
        return href === '#support-calculator' || href === '#taldav-support-calculator';
    }

    document.addEventListener('DOMContentLoaded', function () {
        var modal = getModal();

        if (!modal) {
            return;
        }

        updateCalculator(modal);

        document.addEventListener('click', function (event) {
            var opener = event.target.closest('#taldav-open-calculator, .taldav-open-calculator, [data-taldav-calculator-open], #wp-care-open-calculator');
            var link = event.target.closest('a');

            if (opener || isCalculatorLink(link)) {
                event.preventDefault();
                openCalculator();
                return;
            }

            if (event.target.closest('[data-taldav-calculator-close]')) {
                event.preventDefault();
                closeCalculator();
                return;
            }

            if (event.target.closest('[data-taldav-apply-estimate]')) {
                event.preventDefault();
                applyEstimate();
            }
        });

        modal.querySelectorAll('input[data-price]').forEach(function (input) {
            input.addEventListener('change', function () {
                updateCalculator(modal);
            });
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && !modal.hidden) {
                closeCalculator();
            }
        });
    });
})();
