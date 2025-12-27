/*
CWE-1329: Reliance on Component That is Not Updateable
This file simulates a vendor-supplied, bundled component with no update channel.
Assume it is compiled into device firmware or distributed as a static blob.
*/
(function(){
  var el = document.getElementById('legacy-monitor');
  if (!el) return;
  el.innerHTML = 'Legacy Dashboard Rendered (non-updateable component)';
})();
