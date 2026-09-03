<?php
/**
 * Plugin Name: TalDav Site Tools
 * Description: Site-specific functionality and assets for the TalDav / WP Care portfolio website.
 * Version: 0.4.0
 * Author: TalDav Web Care
 * Text Domain: taldav-site-tools
 */

if (!defined('ABSPATH')) {
    exit;
}

define('TALDAV_SITE_TOOLS_VERSION', '0.4.0');
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
        'open_button_text' => 'Build and Estimate Your Plan',
        'modal_kicker' => 'Custom Portfolio Plugin',
        'modal_title' => 'WordPress Support Calculator',
        'modal_description' => 'This calculator was built specifically for this portfolio website and is part of the portfolio itself: a small, maintainable WordPress plugin instead of fragile page-only code.',
        'discount_label' => 'Discount',
        'total_label' => 'Estimated monthly support',
        'apply_button_text' => 'OK',
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
        'open_button_text' => isset($input['open_button_text']) ? sanitize_text_field($input['open_button_text']) : $defaults['open_button_text'],
        'modal_kicker' => isset($input['modal_kicker']) ? sanitize_text_field($input['modal_kicker']) : $defaults['modal_kicker'],
        'modal_title' => isset($input['modal_title']) ? sanitize_text_field($input['modal_title']) : $defaults['modal_title'],
        'modal_description' => isset($input['modal_description']) ? sanitize_textarea_field($input['modal_description']) : $defaults['modal_description'],
        'discount_label' => isset($input['discount_label']) ? sanitize_text_field($input['discount_label']) : $defaults['discount_label'],
        'total_label' => isset($input['total_label']) ? sanitize_text_field($input['total_label']) : $defaults['total_label'],
        'apply_button_text' => isset($input['apply_button_text']) ? sanitize_text_field($input['apply_button_text']) : $defaults['apply_button_text'],
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
    <tr class=taldav-service-row>
        <td><input name=taldav_site_tools_options[services][<?php echo esc_attr($index); ?>][checked] type=checkbox value=1 <?php checked($service['checked'], 1); ?>></td>
        <td><input name=taldav_site_tools_options[services][<?php echo esc_attr($index); ?>][label] type=text value=<?php echo esc_attr($service['label']); ?> class=regular-text></td>
        <td><input name=taldav_site_tools_options[services][<?php echo esc_attr($index); ?>][description] type=text value=<?php echo esc_attr($service['description']); ?> class=large-text></td>
        <td><input name=taldav_site_tools_options[services][<?php echo esc_attr($index); ?>][price] type=number min=0 step=1 value=<?php echo esc_attr($service['price']); ?> class=small-text></td>
        <td><button type=button class=button taldav-remove-service>Remove</button></td>
    </tr>
    <?php
}

function taldav_site_tools_render_settings_page() {
    if (!current_user_can('manage_options')) {
        return;
    }

    $options = taldav_site_tools_get_options();
    ?>
    <div class=wrap taldav-settings-page>
        <h1>TalDav Site Tools</h1>
        <p>Settings for the custom pricing calculator built specifically for this portfolio website.</p>

        <style>
            .taldav-settings-layout { display: grid; gap: 24px; grid-template-columns: minmax(0, 1fr) 360px; max-width: 1320px; }
            .taldav-settings-card { background: #fff; border: 1px solid #dcdcde; box-shadow: 0 1px 1px rgba(0,0,0,.04); padding: 20px; }
            .taldav-settings-card h2:first-child { margin-top: 0; }
            .taldav-settings-card textarea.large-text { min-height: 96px; }
            .taldav-settings-sidebar { align-self: start; position: sticky; top: 42px; }
            #taldav-services-table input.regular-text, #taldav-services-table input.large-text { width: 100%; }
            @media (max-width: 1100px) { .taldav-settings-layout { grid-template-columns: 1fr; } .taldav-settings-sidebar { position: static; } }
        </style>

        <form method=post action=options.php>
            <?php settings_fields('taldav_site_tools_settings'); ?>

            <div class=taldav-settings-layout>
                <div class=taldav-settings-main>
                    <div class=taldav-settings-card>
                        <h2>Calculator Text</h2>
                        <table class=form-table role=presentation>
                            <tr>
                                <th scope=row><label for=taldav_open_button_text>Open Button Text</label></th>
                                <td><input id=taldav_open_button_text name=taldav_site_tools_options[open_button_text] type=text value=<?php echo esc_attr($options['open_button_text']); ?> class=regular-text></td>
                            </tr>
                            <tr>
                                <th scope=row><label for=taldav_modal_kicker>Top Label</label></th>
                                <td><input id=taldav_modal_kicker name=taldav_site_tools_options[modal_kicker] type=text value=<?php echo esc_attr($options['modal_kicker']); ?> class=regular-text></td>
                            </tr>
                            <tr>
                                <th scope=row><label for=taldav_modal_title>Modal Title</label></th>
                                <td><input id=taldav_modal_title name=taldav_site_tools_options[modal_title] type=text value=<?php echo esc_attr($options['modal_title']); ?> class=large-text></td>
                            </tr>
                            <tr>
                                <th scope=row><label for=taldav_modal_description>Modal Description</label></th>
                                <td><textarea id=taldav_modal_description name=taldav_site_tools_options[modal_description] class=large-text><?php echo esc_textarea($options['modal_description']); ?></textarea></td>
                            </tr>
                            <tr>
                                <th scope=row><label for=taldav_total_label>Total Label</label></th>
                                <td><input id=taldav_total_label name=taldav_site_tools_options[total_label] type=text value=<?php echo esc_attr($options['total_label']); ?> class=regular-text></td>
                            </tr>
                            <tr>
                                <th scope=row><label for=taldav_apply_button_text>Apply Button Text</label></th>
                                <td><input id=taldav_apply_button_text name=taldav_site_tools_options[apply_button_text] type=text value=<?php echo esc_attr($options['apply_button_text']); ?> class=regular-text></td>
                            </tr>
                        </table>
                    </div>

                    <div class=taldav-settings-card style=margin-top: 24px;>
                        <h2>Calculator Services</h2>
                        <p>Add, remove and edit the service items displayed in the calculator.</p>
                        <table class=widefat striped id=taldav-services-table>
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

                        <p><button type=button class=button button-secondary id=taldav-add-service>Add Service</button></p>
                    </div>
                </div>

                <div class=taldav-settings-sidebar>
                    <div class=taldav-settings-card>
                        <h2>Discount</h2>
                        <p>
                            <label>
                                <input name=taldav_site_tools_options[discount_enabled] type=checkbox value=1 <?php checked($options['discount_enabled'], 1); ?>>
                                Enable discount
                            </label>
                        </p>
                        <p>
                            <label for=taldav_discount_label><strong>Discount Label</strong></label><br>
                            <input id=taldav_discount_label name=taldav_site_tools_options[discount_label] type=text value=<?php echo esc_attr($options['discount_label']); ?> class=regular-text>
                        </p>
                        <p>
                            <label for=taldav_discount_min_total><strong>Apply From</strong></label><br>
                            <input id=taldav_discount_min_total name=taldav_site_tools_options[discount_min_total] type=number min=0 step=1 value=<?php echo esc_attr($options['discount_min_total']); ?> class=small-text>
                        </p>
                        <p>
                            <label for=taldav_discount_percent><strong>Discount Percent</strong></label><br>
                            <input id=taldav_discount_percent name=taldav_site_tools_options[discount_percent] type=number min=0 max=100 step=1 value=<?php echo esc_attr($options['discount_percent']); ?> class=small-text>%
                        </p>
                    </div>

                    <div class=taldav-settings-card style=margin-top: 24px;>
                        <h2>Form Integration</h2>
                        <p>The calculator writes values into form fields by their <code>name</code> attribute.</p>
                        <p>
                            <label for=taldav_currency><strong>Currency Symbol</strong></label><br>
                            <input id=taldav_currency name=taldav_site_tools_options[currency] type=text value=<?php echo esc_attr($options['currency']); ?> class=small-text>
                        </p>
                        <p>
                            <label for=taldav_form_selector><strong>Optional Form CSS Selector</strong></label><br>
                            <input id=taldav_form_selector name=taldav_site_tools_options[form_selector] type=text value=<?php echo esc_attr($options['form_selector']); ?> class=regular-text placeholder=.fluent_form_5>
                        </p>
                        <p>
                            <label for=taldav_price_field_name><strong>Price Field Name</strong></label><br>
                            <input id=taldav_price_field_name name=taldav_site_tools_options[price_field_name] type=text value=<?php echo esc_attr($options['price_field_name']); ?> class=regular-text>
                        </p>
                        <p>
                            <label for=taldav_services_field_name><strong>Services Field Name</strong></label><br>
                            <input id=taldav_services_field_name name=taldav_site_tools_options[services_field_name] type=text value=<?php echo esc_attr($options['services_field_name']); ?> class=regular-text>
                        </p>
                    </div>

                    <?php submit_button(); ?>
                </div>
            </div>

            <template id=taldav-service-row-template>
                <tr class=taldav-service-row>
                    <td><input name=taldav_site_tools_options[services][__INDEX__][checked] type=checkbox value=1></td>
                    <td><input name=taldav_site_tools_options[services][__INDEX__][label] type=text value=" class=regular-text></td>
                    <td><input name=taldav_site_tools_options[services][__INDEX__][description] type=text value=" class=large-text></td>
                    <td><input name=taldav_site_tools_options[services][__INDEX__][price] type=number min=0 step=1 value=0 class=small-text></td>
                    <td><button type=button class=button taldav-remove-service>Remove</button></td>
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
    <div class=taldav-calculator-block>
        <button type=button id=taldav-open-calculator class=taldav-calculator-primary><?php echo esc_html($options['open_button_text']); ?></button>

        <div id="taldav-support-calculator" class="taldav-calculator-modal" hidden data-currency="<?php echo esc_attr($options['currency']); ?>" data-discount-enabled="<?php echo esc_attr($options['discount_enabled']); ?>" data-discount-min-total="<?php echo esc_attr($options['discount_min_total']); ?>" data-discount-percent="<?php echo esc_attr($options['discount_percent']); ?>" data-form-selector="<?php echo esc_attr($options['form_selector']); ?>" data-price-field-name="<?php echo esc_attr($options['price_field_name']); ?>" data-services-field-name="<?php echo esc_attr($options['services_field_name']); ?>">
            <div class=taldav-calculator-backdrop data-taldav-calculator-close></div>
            <div class=taldav-calculator-dialog role=dialog aria-modal=true aria-labelledby=taldav-calculator-title>
                <button type=button class=taldav-calculator-close aria-label=Close calculator data-taldav-calculator-close>&times;</button>

                <div class=taldav-calculator-header>
                    <p class=taldav-calculator-kicker><?php echo esc_html($options['modal_kicker']); ?></p>
                    <h3 id=taldav-calculator-title><?php echo esc_html($options['modal_title']); ?></h3>
                    <p><?php echo esc_html($options['modal_description']); ?></p>
                </div>

                <div class=taldav-calculator-options>
                    <?php foreach ($options['services'] as $service) : ?>
                        <label class=taldav-calculator-option>
                            <input type="checkbox" data-price="<?php echo esc_attr($service['price']); ?>" data-label="<?php echo esc_attr($service['label']); ?>" <?php checked($service['checked'], 1); ?>>
                            <span>
                                <strong><?php echo esc_html($service['label']); ?></strong>
                                <small><?php echo esc_html($service['description']); ?></small>
                            </span>
                            <b><?php echo esc_html($options['currency']); ?><?php echo esc_html(number_format_i18n((float) $service['price'], 0)); ?></b>
                        </label>
                    <?php endforeach; ?>
                </div>

                <div class=taldav-calculator-discount data-taldav-discount-row hidden>
                    <span><?php echo esc_html($options['discount_label']); ?></span>
                    <strong data-taldav-discount>0</strong>
                </div>

                <div class=taldav-calculator-result>
                    <span><?php echo esc_html($options['total_label']); ?></span>
                    <strong><span data-taldav-total>0</span></strong>
                </div>

                <div class=taldav-calculator-actions>
                    <button type=button class=taldav-calculator-primary data-taldav-apply-estimate><?php echo esc_html($options['apply_button_text']); ?></button>
                </div>
            </div>
        </div>
    </div>
    <?php

    return ob_get_clean();
}
add_shortcode('taldav_support_calculator', 'taldav_site_tools_support_calculator_shortcode');

function taldav_site_tools_admin_sidebar_width_fix() {
    $screen = function_exists('get_current_screen') ? get_current_screen() : null;

    if (!$screen || $screen->id !== 'settings_page_taldav-site-tools') {
        return;
    }
    ?>
    <style>
        .taldav-settings-sidebar input.regular-text,
        .taldav-settings-sidebar input[type=text],
        .taldav-settings-sidebar input[type=number] {
            box-sizing: border-box;
            max-width: 100%;
            width: 100%;
        }

        .taldav-settings-sidebar input.small-text {
            max-width: 96px;
            width: 96px;
        }
    </style>
    <?php
}
add_action('admin_head', 'taldav_site_tools_admin_sidebar_width_fix');
