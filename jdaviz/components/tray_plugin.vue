<template>
  <v-container 
    class="tray-plugin"
    style="padding-left: 24px; padding-right: 24px; padding-top: 12px" >
    <v-row>
      <div style="width: calc(100% - 32px)">
        <j-docs-link :link="link">{{ description }}</j-docs-link>
      </div>

      <div style="width: 32px">
        <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
      </div>
    </v-row>

    <v-row v-if="isDisabled()">
      <span> {{ getDisabledMsg() }}</span>
    </v-row>
    <div v-else>
      <v-row v-if="uses_active_status && keep_active !== undefined" style="padding-bottom: 24px">
        <!-- TODO: update:keep_active is not working!!! -->
        <plugin-switch
          :value.sync="keep_active"
          @update:value="$emit('update:keep_active', $event)"
          label="Keep active"
          api_hint="plg.keep_active = "
          :api_hints_enabled="api_hints_enabled"
          hint="Consider plugin active (showing any previews and enabling all keypress events) even when not opened"
        />
      </v-row>

      <slot></slot>
    </div>
  </v-container>
</template>

<script>
module.exports = {
  props: ['config', 'plugin_key', 'irrelevant_msg', 'disabled_msg', 'description',
          'api_hints_enabled', 'link', 'popout_button',
          'uses_active_status', 'keep_active', 'scroll_to'],
  methods: {
    boolToString(b) {
      if (b) {
        return 'True'
      } else {
        return 'False'
      }
    },
    isDisabled() {
      return this.getDisabledMsg().length > 0
    },
    getDisabledMsg() {
      return this.irrelevant_msg || this.disabled_msg || ''
    },
    sendPing(recursive) {
      if (!this.$el.isConnected) {
        return
      }
      if (!document.hidden) {
        this.$emit('plugin-ping', Date.now())
      }
      if (this.scroll_to) {
        this.$emit('update:scroll_to', false)
        this.$el.scrollIntoView({behavior: "smooth", block: "nearest", inline: "start"});
      }
      if (!recursive) {
        return
      }
      setTimeout(() => {
        this.sendPing(true)          
      }, 200)  // ms
    },
    checkNotebookContext() {
      // copied from app.vue
      this.notebook_context = document.getElementById("ipython-main-app")
        || document.querySelector('.jp-LabShell')
        || document.querySelector(".lm-Widget#main"); /* Notebook 7 */
      return this.notebook_context;
    },
  },
  mounted() {
    this.sendPing(true);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        this.sendPing(false)
      }
    });
  },
};
</script>

<style scoped>
  .row {
    margin-bottom: 12px !important;
  }

  .row-min-bottom-padding {
    margin-bottom: 4px !important;
  }

  .row-no-outside-padding .col:first-of-type {
    padding-left: 0px !important;
  }

  .row-no-vertical-padding-margin {
    padding-top: 0px !important;
    padding-bottom: 0px !important;
    margin-bottom: 0px !important;
    margin-top: 0px !important;
  }

  .row-no-outside-padding .col:last-of-type {
    padding-right: 0px !important;
  }

  .row-no-padding > .col {
    padding-left: 0px !important;
    padding-right: 0px !important;
  }

  .v-expansion-panel-header {
    /* tighten default padding on any sub expansion headers */
    padding: 6px !important;
  }
  
  .v-expansion-panel-header .row {
    /* override margin from above and replace with equal top and bottom margins
    for the text in the panel header */
    margin-top: 2px !important;
    margin-bottom: 2px !important;
  }
</style>
