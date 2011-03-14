var notify;

var setnotifier = function(data) {
  $(notify).next('span').text(data).fadeIn().delay(1000).fadeOut();
};

var setdefaultclient = function(tid, elem) {
  var splitTid = tid.split('-');
  notify = elem;

  $.ajax({
    url: '/admin/clients/'+ splitTid[0]+'/'+ splitTid[1]+'/_setdefault',
    success: function(data) {
      setnotifier(data);
    }
  });
};

$(document).ready(function() {

  $('#oslist select').change(function() {
    tid = $(this).children('option:selected').attr('value');
    setdefaultclient(tid, $(this));
  });

});
