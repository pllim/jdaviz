<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Markers"
    :description="docs_description || 'Create and export markers.  Press m with the cursor over a viewer to log the mouseover information.  To change the selected layer, click the layer cycler in the mouseover information section of the app-level toolbar.'"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#markers'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <jupyter-widget :widget="table_widget"></jupyter-widget> 

  </j-tray-plugin>
</template>
