import("etherpad.log");
import("dispatch.{Dispatcher,PrefixMatcher,forward}");
import("plugins.ethertex.controllers.ethertex2");

function serverStartup() {
 log.info("Server startup for EtherTeX2e");
}

function serverShutdown() {
 log.info("Server shutdown for EtherTeX2e");
}

function handlePath() {
 return [[PrefixMatcher('/build/'), forward(ethertex2)]];

}
