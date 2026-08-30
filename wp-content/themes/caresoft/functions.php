<?php
/**
 * Theme functions and definitions
 *
 * @package CareSoft
 */

/**
 * After setup theme hook
 */
function caresoft_theme_setup(){
    /*
     * Make child theme available for translation.
     * Translations can be filed in the /languages/ directory.
     */
    load_child_theme_textdomain( 'caresoft' );	
}
add_action( 'after_setup_theme', 'caresoft_theme_setup' );

/**
 * Load assets.
 */

function caresoft_theme_css() {
	wp_enqueue_style( 'caresoft-parent-theme-style', get_template_directory_uri() . '/style.css' );
}
add_action( 'wp_enqueue_scripts', 'caresoft_theme_css', 99);


require get_stylesheet_directory() . '/theme-functions/controls/class-customize.php';


/**
 * Import Options From Parent Theme
 *
 */
function caresoft_parent_theme_options() {
	$softme_mods = get_option( 'theme_mods_softme' );
	if ( ! empty( $softme_mods ) ) {
		foreach ( $softme_mods as $softme_mod_k => $softme_mod_v ) {
			set_theme_mod( $softme_mod_k, $softme_mod_v );
		}
	}
}
add_action( 'after_switch_theme', 'caresoft_parent_theme_options' );