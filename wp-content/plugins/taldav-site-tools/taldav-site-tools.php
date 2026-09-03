<?php
/**
 * Plugin Name: TalDav Site Tools
 * Description: Site-specific functionality and assets for the TalDav / WP Care portfolio website.
 * Version: 0.3.0
 * Author: TalDav Web Care
 * Text Domain: taldav-site-tools
 */

if (!defined('ABSPATH')) {
    exit;
}

define('TALDAV_SITE_TOOLS_VERSION', '0.3.0');
define('TALDAV_SITE_TOOLS_DIR', plugin_dir_path(__FILE__));
define('TALDAV_SITE_TOOLS_URL', plugin_dir_url(__FILE__));

function taldav_site_tools_default_services() {
    return array(
        array(
            'label' => 'Content updates',
            'description' => 'Text, images, pages and small content changes.',
            'price' => 120,
            'checked' => 1,
        ),
        array(
            'label' => 'Plugin and theme checks',
            'description' => 'Regular checks before updates and visible issues.',
            'price' => 90,
            'checked' => 1,
        ),
        array(
            'label' => 'Backups review',
            'description' => 'Check that files and database backups are in place.',
            'price' => 70,
            'checked' => 1,
        ),
        array(
            'label' => 'Small technical fixes',
            'description' => 'Minor layout fixes, settings checks and simple troubleshooting.',
            'price' => 110,
            'checked' => 0,
        ),
    );
}

function taldav_site_tools_default_options() {
    return array(
        'currency' => '$',
        'discount_enabled' => 1,
        'discount_min_total' => 250,
        'discount_percent' => 10,
        'form_selector' => '',
        'price_field_name' => 'estimated_monthly_price',
        'services_field_name' => 'selected_custom_services',
        'services' => taldav_site_tools_default_services(),
    );
}

function taldav_site_tools_normalize_services($services) {
    if (!is_array($services) || empty($services)) {
        return taldav_site_tools_default_services();
    }

    $normalized = array();

    foreach ($services as $service) {
        if (!is_array($service)) {
            continue;
        }

        $label = isset($service['label']) ? trim((string) $service['label']) : '';

        if ($label === '') {
            continue;
        }

        $normalized[] = array(
            'label' => $label,
            'description' => isset($service['description']) ? (string) $service['description'] : '',
            'price' => isset($service['price']) ? max(0, (float) $service['price']) : 0,
            'checked' => empty($service['checked']) ? 0 : 1,
        );
    }

    return !empty($normalized) ? $normalized : taldav_site_tools_default_services();
}

function taldav_site_tools_get_options() {
    $defaults = taldav_site_tools_default_options();
    $saved = get_option('taldav_site_tools_options', array());

    if (!is_array($saved)) {
        return $defaults;
    }

    $options = wp_parse_args($saved, $defaults);
    $options['services'] = isset($saved['services']) ? taldav_site_tools_normalize_services($saved['services']) : $defaults['services'];

    return $options;
}

function taldav_site_tools_sanitize_options($input) {
    $defaults = taldav_site_tools_default_options();
    $input = is_array($input) ? $input : array();

    return array(
        'currency' => isset($input['currency']) ? sanitize_text_field($input['currency']) : $defaults['currency'],
        'discount_enabled' => empty($input['discount_enabled']) ? 0 : 1,
        'discount_min_total' => isset($input['discount_min_total']) ? max(0, (float) $input['discount_min_total']) : $defaults['discount_min_total'],
        'discount_percent' => isset($input['discount_percent']) ? min(100, max(0, (float) $input['discount_percent'])) : $defaults['discount_percent'],
        'form_selector' => isset($input['form_selector']) ? sanitize_text_field($input['form_selector']) : '',
        'price_field_name' => isset($input['price_field_name']) ? sanitize_text_field($input['price_field_name']) : $defaults['price_field_name'],
        'services_field_name' => isset($input['services_field_name']) ? sanitize_text_field($input['services_field_name']) : $defaults['services_field_name'],
        'services' => taldav_site_tools_normalize_services($input['services'] ?? array()),
    );
}

function taldav_site_tools_admin_menu() {
    add_options_page(
        'TalDav Site Tools',
        'TalDav Site Tools',
        'manage_options',
        'taldav-site-tools',
        'taldav_site_tools_render_settings_page'
    );
}
add_action('admin_menu', 'taldav_site_tools_admin_menu');

function taldav_site_tools_register_settings() {
    register_setting(
        'taldav_site_tools_settings',
        'taldav_site_tools_options',
        array('sanitize_callback' => 'taldav_site_tools_sanitize_options')
    );
}
add_action('admin_init', 'taldav_site_tools_register_settings');

function taldav_site_tools_render_service_row($index, $service) {
    ?>
    <tr class='taldav-service-row'>
        <td><input name='taldav_site_tools_options[services][<?php echo esc_attr($index); ?>][checked]' type='checkbox' value='1' <?php checked($service['checked'], 1); ?>></td>
        <td><input name='taldav_site_tools_options[services][<?php echo esc_attr($index); ?>][label]' type='text' value='<?php echo esc_attr($service['label']); ?>' class='regular-text'></td>
        <td><input name='taldav_site_tools_options[services][<?php echo esc_attr($index); ?>][description]' type='text' value='<?php echo esc_attr($service['description']); ?>' class='large-text'></td>
        <td><input name='taldav_site_tools_options[services][<?php echo esc_attr($index); ?>][price]' type='number' min='0' step='1' value='<?php echo esc_attr($service['price']); ?>' class='small-text'></td>
        <td><button type='button' class='button taldav-remove-service'>Remove</button></td>
    </tr>
    <?php
}

function taldav_site_tools_render_settings_page() {
    if (!current_user_can('manage_options')) {
        return;
    }

    $options = taldav_site_tools_get_options();
    ?>
    <div class='wrap'>
        <h1>TalDav Site Tools</h1>
        <p>Settings for the custom pricing calculator built specifically for this portfolio website.</p>

        <form method='post' action='options.php'>
            <?php settings_fields('taldav_site_tools_settings'); ?>

            <h2>Pricing Calculator</h2>
            <table class='form-table' role='presentation'>
                <tr>
                    <th scope='row'><label for='taldav_currency'>Currency Symbol</label></th>
                    <td><input id='taldav_currency' name='taldav_site_tools_options[currency]' type='text' value='<?php echo esc_attr($options['currency']); ?>' class='small-text'></td>
                </tr>
                <tr>
                    <th scope='row'>Discount</th>
                    <td>
                        <label>
                            <input name='taldav_site_tools_options[discount_enabled]' type='checkbox' value='1' <?php checked($options['discount_enabled'], 1); ?>>
                            Enable discount when the subtotal reaches the configured threshold.
                        </label>
                        <p>
                            <label>Threshold: <input name='taldav_site_tools_options[discount_min_total]' type='number' min='0' step='1' value='<?php echo esc_attr($options['discount_min_total']); ?>' class='small-text'></label>
                            <label style='margin-left: 16px;'>Discount: <input name='taldav_site_tools_options[discount_percent]' type='number' min='0' max='100' step='1' value='<?php echo esc_attr($options['discount_percent']); ?>' class='small-text'>%</label>
                        </p>
                    </td>
                </tr>
            </table>

            <h2>Form Integration</h2>
            <p>The calculator writes values into form fields by their <code>name</code> attribute. The optional form selector limits the search to one form.</p>
            <table class='form-table' role='presentation'>
                <tr>
                    <th scope='row'><label for='taldav_form_selector'>Optional Form CSS Selector</label></th>
                    <td>
                        <input id='taldav_form_selector' name='taldav_site_tools_options[form_selector]' type='text' value='<?php echo esc_attr($options['form_selector']); ?>' class='regular-text' placeholder='.fluent_form_5'>
                        <p class='description'>Leave empty to search the whole page.</p>
                    </td>
                </tr>
                <tr>
                    <th scope='row'><label for='taldav_price_field_name'>Price Field Name</label></th>
                    <td><input id='taldav_price_field_name' name='taldav_site_tools_options[price_field_name]' type='text' value='<?php echo esc_attr($options['price_field_name']); ?>' class='regular-text'></td>
                </tr>
                <tr>
                    <th scope='row'><label for='taldav_services_field_name'>Services Field Name</label></th>
                    <td><input id='taldav_services_field_name' name='taldav_site_tools_options[services_field_name]' type='text' value='<?php echo esc_attr($options['services_field_name']); ?>' class='regular-text'></td>
                </tr>
            </table>

            <h2>Services</h2>
            <table class='widefat striped' id='taldav-services-table'>
                <thead>
                    <tr>
                        <th>Default</th>
                        <th>Label</th>
                        <th>Description</th>
                        <th>Monthly Price</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($options['services'] as $index => $service) : ?>
                        <?php taldav_site_tools_render_service_row($index, $service); ?>
                    <?php endforeach; ?>
                </tbody>
            </table>

            <p><button type='button' class='button button-secondary' id='taldav-add-service'>Add Service</button></p>

            <template id='taldav-service-row-template'>
                <tr class='taldav-service-row'>
                    <td><input name='taldav_site_tools_options[services][__INDEX__][checked]' type='checkbox' value='1'></td>
                    <td><input name='taldav_site_tools_options[services][__INDEX__][label]' type='text' value='' class='regular-text'></td>
                    <td><input name='taldav_site_tools_options[services][__INDEX__][description]' type='text' value='' class='large-text'></td>
                    <td><input name='taldav_site_tools_options[services][__INDEX__][price]' type='number' min='0' step='1' value='0' class='small-text'></td>
                    <td><button type='button' class='button taldav-remove-service'>Remove</button></td>
                </tr>
            </template>

            <script>
                document.addEventListener('DOMContentLoaded', function () {
                    var tableBody = document.querySelector('#taldav-services-table tbody');
                    var addButton = document.getElementById('taldav-add-service');
                    var template = document.getElementById('taldav-service-row-template');

                    if (!tableBody || !addButton || !template) {
                        return;
                    }

                    addButton.addEventListener('click', function () {
                        var index = 'new_' + Date.now();
                        var html = template.innerHTML.replaceAll('__INDEX__', index);
                        tableBody.insertAdjacentHTML('beforeend', html);
                    });

                    tableBody.addEventListener('click', function (event) {
                        var button = event.target.closest('.taldav-remove-service');

                        if (!button) {
                            return;
                        }

                        event.preventDefault();
                        button.closest('tr').remove();
                    });
                });
            </script>

            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}

function taldav_site_tools_asset_version($relative_path) {
    $file_path = TALDAV_SITE_TOOLS_DIR . $relative_path;

    if (file_exists($file_path)) {
        return (string) filemtime($file_path);
    }

    return TALDAV_SITE_TOOLS_VERSION;
}

function taldav_site_tools_register_assets() {
    wp_register_style(
        'taldav-pricing',
        TALDAV_SITE_TOOLS_URL . 'assets/css/pricing.css',
        array(),
        taldav_site_tools_asset_version('assets/css/pricing.css')
    );

    wp_register_script(
        'taldav-support-calculator',
        TALDAV_SITE_TOOLS_URL . 'assets/js/support-calculator.js',
        array(),
        taldav_site_tools_asset_version('assets/js/support-calculator.js'),
        true
    );
}
add_action('wp_enqueue_scripts', 'taldav_site_tools_register_assets');

function taldav_site_tools_enqueue_pricing_assets() {
    if (is_page('pricing')) {
        wp_enqueue_style('taldav-pricing');
        wp_enqueue_script('taldav-support-calculator');
    }
}
add_action('wp_enqueue_scripts', 'taldav_site_tools_enqueue_pricing_assets');

function taldav_site_tools_support_calculator_shortcode() {
    $options = taldav_site_tools_get_options();

    wp_enqueue_style('taldav-pricing');
    wp_enqueue_script('taldav-support-calculator');

    ob_start();
    ?>
    <div class='taldav-calculator-block'>
        <button type='button' id='taldav-open-calculator' class='taldav-calculator-primary'>Build and Estimate Your Plan</button>

        <div id='taldav-support-calculator' class='taldav-calculator-modal' hidden data-currency='<?php echo esc_attr($options['currency']); ?>' data-discount-enabled='<?php echo esc_attr($options['discount_enabled']); ?>' data-discount-min-total='<?php echo esc_attr($options['discount_min_total']); ?>' data-discount-percent='<?php echo esc_attr($options['discount_percent']); ?>' data-form-selector='<?php echo esc_attr($options['form_selector']); ?>' data-price-field-name='<?php echo esc_attr($options['price_field_name']); ?>' data-services-field-name='<?php echo esc_attr($options['services_field_name']); ?>'>
            <div class='taldav-calculator-backdrop' data-taldav-calculator-close></div>
            <div class='taldav-calculator-dialog' role='dialog' aria-modal='true' aria-labelledby='taldav-calculator-title'>
                <button type='button' class='taldav-calculator-close' aria-label='Close calculator' data-taldav-calculator-close>&times;</button>

                <div class='taldav-calculator-header'>
                    <p class='taldav-calculator-kicker'>Custom Portfolio Plugin</p>
                    <h3 id='taldav-calculator-title'>WordPress Support Calculator</h3>
                    <p>This calculator was built specifically for this portfolio website and is part of the portfolio itself: a small, maintainable WordPress plugin instead of fragile page-only code.</p>
                </div>

                <div class='taldav-calculator-options'>
                    <?php foreach ($options['services'] as $service) : ?>
                        <label class='taldav-calculator-option'>
                            <input type='checkbox' data-price='<?php echo esc_attr($service['price']); ?>' data-label='<?php echo esc_attr($service['label']); ?>' <?php checked($service['checked'], 1); ?>>
                            <span>
                                <strong><?php echo esc_html($service['label']); ?></strong>
                                <small><?php echo esc_html($service['description']); ?></small>
                            </span>
                            <b><?php echo esc_html($options['currency']); ?><?php echo esc_html(number_format_i18n((float) $service['price'], 0)); ?></b>
                        </label>
                    <?php endforeach; ?>
                </div>

                <div class='taldav-calculator-discount' data-taldav-discount-row hidden>
                    <span>Discount</span>
                    <strong data-taldav-discount>0</strong>
                </div>

                <div class='taldav-calculator-result'>
                    <span>Estimated monthly support</span>
                    <strong><span data-taldav-total>0</span></strong>
                </div>

                <div class='taldav-calculator-actions'>
                    <button type='button' class='taldav-calculator-primary' data-taldav-apply-estimate>OK</button>
                </div>
            </div>
        </div>
    </div>
    <?php

    return ob_get_clean();
}
add_shortcode('taldav_support_calculator', 'taldav_site_tools_support_calculator_shortcode');
