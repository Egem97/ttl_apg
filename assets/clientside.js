// Clientside functions for better performance
if (!window.dash_clientside) {
    window.dash_clientside = {};
}

window.dash_clientside.clientside = {
    update_ag_grid_theme: function(switch_on) {
        // Return the appropriate theme class based on the toggle state
        return switch_on ? "ag-theme-alpine-dark" : "ag-theme-alpine";
    }
};
