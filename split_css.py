import re

with open('frontend/css/dashboard.css', 'r', encoding='utf-8') as f:
    css = f.read()

# The split points:
# dashboard-layout.css gets everything from top to /* -- Page content -- */, AND the Responsive section at the bottom (before Profile).
# Wait, let's just manually string manipulate.

# 1. Profile Module Styles
profile_idx = css.find('/* ---------------------------------------------------------------\n   PROFILE MODULE STYLES')
if profile_idx != -1:
    profile_css = css[profile_idx:]
    css_without_profile = css[:profile_idx]
    with open('frontend/css/profile.css', 'w', encoding='utf-8') as f:
        f.write(profile_css)
else:
    css_without_profile = css

# 2. Extract layout vs dashboard
page_content_idx = css_without_profile.find('/* -- Page content ----------------------------------------------------------- */')
responsive_idx = css_without_profile.find('/* -- Responsive ------------------------------------------------------------- */')

layout_css = css_without_profile[:page_content_idx] + css_without_profile[responsive_idx:]
dash_css = css_without_profile[page_content_idx:responsive_idx]

with open('frontend/css/dashboard-layout.css', 'w', encoding='utf-8') as f:
    f.write(layout_css)
    
with open('frontend/css/dashboard.css', 'w', encoding='utf-8') as f:
    f.write(dash_css)

print('CSS split successfully.')
