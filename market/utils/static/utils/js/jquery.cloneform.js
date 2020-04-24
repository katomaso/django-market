(function($){

    $.fn.cloneForm = function(options) {
        var opts = $.extend({}, $.fn.cloneForm.defaults, options);

        var prefix = $('input, select', this).first().attr('name').split('-')[0];
        var formCounter = $('#id_' + prefix + '-TOTAL_FORMS')
            .attr('autocomplete', 'off');
        var currentCount = parseInt(formCounter.val(), 10);

        var newForm = this.clone();

        // replace 'id', 'name' and 'for' attributes on elements
        var id_regex = new RegExp('(' + prefix + '-\\d+)');
        var replacement = prefix + '-' + currentCount;
        $('input, select, textarea, a', newForm).each(function(){
            var el = this,
                $el = $(this),
                old_id = $el.attr('id');

            if (el.id) el.id = el.id.replace(id_regex, replacement);
            if (el.name) el.name = el.name.replace(id_regex, replacement);
            // do not clone field values
            $(this).val('');
            // initial value for twitter
            if ($el.parent().hasClass('twitter')) $(this).val('@');

            //FIXME? cloned checkboxes and radios don't work for some reason...
            if ($el.is(':checkbox, :radio')) {
                var attrs = {type: el.type, id: el.id, name: el.name};
                if ($el.is(':radio'))
                    attrs['value'] = $('#' + old_id).val();
                var newInput = $('<input/>', attrs).insertAfter(el);
                if ($el.attr('disabled')) {
                    newInput.attr('disabled', 'disabled');
                }
                $el.remove();
            }
        });
        $('label', newForm).each(function(){
            var label = $(this);
            var oldFor = label.attr('for');
            if (oldFor)
                label.attr('for', oldFor.replace(id_regex, replacement));
        });
        // do not clone errors
        $('.errormsg', newForm).remove();

        // last added form can be removed
        var oldDeleteLink = this.find(opts.deleteLink).hide();
        var deleteLink = newForm.find(opts.deleteLink).show();
        deleteLink.click(function(){
            newForm.remove();
            formCounter.val(currentCount);
            if (opts.allowDeleteOriginal) {
                oldDeleteLink.show();
            }
            opts.onDelete(newForm);
            return false;
        });

        var newCount = currentCount + 1;
        formCounter.val(newCount);
        newForm.insertAfter(this);
        $('input, select', newForm).first().focus();
        opts.callback.call(this, newForm, newCount);
        newForm.removeClass('marked-for-deletion');
        return newForm;
    };
    $.fn.cloneForm.defaults = {
        callback: function(){},
        onDelete: function(){},
        deleteLink: '.delete-link',
        allowDeleteOriginal: false
    };

})(jQuery);
