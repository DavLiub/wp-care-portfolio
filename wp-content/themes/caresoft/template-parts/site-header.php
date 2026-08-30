<?php  do_action('softme_site_preloader'); ?>	
<?php  do_action('softme_wp_hdr_image'); ?>
<?php 
$softme_hs_hdr_sticky = get_theme_mod( 'softme_hs_hdr_sticky','1');
?>
<header id="dt_header" class="dt_header header--six">
	<div class="dt_header-inner">
		<div class="dt_header-topbar dt-d-lg-block dt-d-none">
			<?php do_action('softme_site_header'); ?>
		</div>
		<div class="dt_header-navwrapper">
			<div class="dt_header-navwrapperinner">
				<!--=== / Start: DT_Navbar / === -->
				<div class="dt_navbar dt-d-none dt-d-lg-block">
					<div class="dt_navbar-wrapper <?php if($softme_hs_hdr_sticky=='1'): esc_attr_e('is--sticky','caresoft'); endif; ?>">
						<div class="dt-container">
							<div class="dt-row">
								<div class="dt-col-3">
									<div class="site--logo">
										<?php do_action('softme_site_logo'); ?>
									</div>
								</div>
								<div class="dt-col-9">
									<div class="dt_navbar-menu">
										<nav class="dt_navbar-nav">
											<?php do_action('softme_site_header_navigation'); ?>
										</nav>
										<div class="dt_navbar-right">
											<ul class="dt_navbar-list-right">    
												<?php do_action('softme_woo_cart'); ?>
												<?php do_action('softme_site_main_search'); ?>
												<?php do_action('softme_hdr_account'); ?>
												<?php do_action('softme_header_button'); ?>
											</ul>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
				<!--=== / End: DT_Navbar / === -->
				<!--=== / Start: DT_Mobile Menu / === -->
				<div class="dt_mobilenav <?php if($softme_hs_hdr_sticky=='1'): esc_attr_e('is--sticky','caresoft'); endif; ?> dt-d-lg-none">
					<div class="dt_mobilenav-topbar">
						<button type="button" class="dt_mobilenav-topbar-toggle"><i class="fas fa-angle-double-down" aria-hidden="true"></i></button>
						<div class="dt_mobilenav-topbar-content">
							<div class="dt-container">
								<div class="dt-row">
									<div class="dt-col-12">
										<?php do_action('softme_site_header'); ?>
									</div>
								</div>
							</div>
						</div>
					</div>
					<div class="dt-container">
						<div class="dt-row">
							<div class="dt-col-12">
								<div class="dt_mobilenav-menu">
									<div class="dt_mobilenav-logo">
										<div class="site--logo">
											<?php do_action('softme_site_mobile_logo'); ?>
										</div>
									</div>
									<div class="dt_mobilenav-toggles">
										<div class="dt_mobilenav-right">
											<ul class="dt_navbar-list-right">                                                 
												<?php do_action('softme_site_main_search'); ?>                                              
												<?php do_action('softme_header_button'); ?>	
											</ul>
										</div>
										<div class="dt_mobilenav-mainmenu">
											<button type="button" class="hamburger dt_mobilenav-mainmenu-toggle">
												<span></span>
												<span></span>
												<span></span>
											</button>
											<nav class="dt_mobilenav-mainmenu-content">
												<div class="dt_header-closemenu off--layer"></div>
												<div class="dt_mobilenav-mainmenu-inner">
													<button type="button" class="dt_header-closemenu site--close"></button>
													<?php do_action('softme_site_header_navigation'); ?>
												</div>
											</nav>
										</div>
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
				<!--=== / End: DT_Mobile Menu / === -->
			</div>
		</div>
	</div>
</header>