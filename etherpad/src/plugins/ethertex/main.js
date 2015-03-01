import("etherpad.log");
import("plugins.ethertex.hooks");
import("plugins.ethertex.static.js.main");

function ethertexInit() {
 this.hooks = ['serverStartup', 'serverShutdown', 'handlePath'];
 this.client = new main.ethertexInit();
 this.description = 'EtherTeX2e - the next generation';
 this.serverStartup = hooks.serverStartup;
 this.serverShutdown = hooks.serverShutdown;
 this.handlePath = hooks.handlePath;
 this.install = install;
 this.uninstall = uninstall;
}

function install() {
 log.info("Installing EtherTeX2");
}

function uninstall() {
 log.info("Uninstalling EtherTeX2");
}

