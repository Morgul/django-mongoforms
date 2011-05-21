/**
 * Created by .
 * User: sunrize
 * Date: 28.04.11
 * Time: 17:41
 */
//MongoListField
(function($) {
    function createListItem(id, title, click) {
        return $("<a href=\"#\" rel=\"" + id + "\">" + title + "</a>").button({
                    'icons': {'secondary':'ui-icon-minus'}
                }).click(click);
    }

    function init(options) {
        return this.each(function() {
            var $this = $(this);
            var current_settings = {};
            $.extend(current_settings, settings, options);
            $this.data(current_settings);
            $this.append('<input type="hidden" name="' + current_settings.name + '">');
            $this.append('<div class="listfield-selected-items"></div>');
            $this.append('<div class="listfield-new-item"></div>');
            $this.addClass('listfield').addClass('ui-widget-content');
            $this.mongoListField('update');
        });
    }

    function update(choices, selected) {
        return this.each(function() {
            var $this = $(this);
            if (!choices) {
                choices = $this.data('choices');
            }
            if (!selected) {
                selected = $this.data('value');
            }

            var listItemGenerator = $this.data('listItemGenerator');
            var $selectedItems = $this.children('.listfield-selected-items');
            $selectedItems.empty();
            var $item;
            var id;
            $.each(selected, function(index, id) {
                var title;
                if (choices) {
                    title = choices[id];
                }
                else {
                    title = id;
                }
                $item = listItemGenerator(id, title, function() {
                    $this.mongoListField('remove', $(this).attr('rel'));
                    return false;
                });
                $selectedItems.append($item);
            });
            if ($selectedItems.length) {
                $selectedItems.show();
            }
            else {
                $selectedItems.hide();
            }

            var $newItem = $this.children('.listfield-new-item');
            $newItem.empty();

            var $input;
            var newItemVisible = false;
            if ( choices && !$.isEmptyObject(choices) ) {
                $input = $("<select id='listfield-new-item-input'></select>");
                $.each(choices, function(id, choice) {
                    if (selected.indexOf(id) == -1) {
                        $input.append("<option value=\"" + id + "\">" + choice + "</option>");
                        newItemVisible = true;
                    }
                });
                if (newItemVisible) {
                    $newItem.append($input);
                }
            }
            else {
                $input = $("<input id='listfield-new-item-input' type='text'>");
                $newItem.append($input);
                newItemVisible = true;
            }

            if (newItemVisible) {
                var $addButton = $('<a href="#" rel="add">Add</a>').button({
                    icons: {'primary': 'ui-icon-plus'}
                }).click(function () {
                    id = $this.find('#listfield-new-item-input').val();
                    $this.mongoListField('add', id);
                    return false;
                });
                $newItem.append($addButton);
                $newItem.show();
            }
            else {
                $newItem.hide();
            }

            $input = $this.children('input').val(JSON.stringify(selected));
        });
    }

    function add(id) {
        return this.each(function() {
            var $this = $(this);
            var selected = $this.data('value');
            if (id && selected.indexOf(id) == -1) {
                selected.push(id);
            }
            $this.mongoListField('update');
        });
    }

    function remove(id) {
        return this.each(function() {
            var $this = $(this);
            var selected = $this.data('value');
            var index = selected.indexOf(id);
            if (index != -1) {
                selected.splice(index, 1);
            }
            $this.mongoListField('update');
        });
    }

    var methods = {
        'update': update,
        'add': add,
        'remove': remove,
        'init': init
    };

    var settings = {
        listItemGenerator: createListItem,
        choices: null,
        value: []
    };

    $.fn.mongoListField = function(method) {
        // Method calling logic
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        }
        else if (typeof method === 'object' || ! method) {
            return methods.init.apply(this, arguments);
        }
        else {
            $.error('Method ' +  method + ' does not exist on jQuery.mongoListField');
        }
    };
})(jQuery);


//MongoDictField
(function($) {
    function createItem(id, title, value, choices) {
        var inputID = "dictitem-" + id;
        var $item = $('<p></p>');
        if (value === undefined) {
            value = '';
        }
        $item.append('<label for="' + inputID + '">' + title + ':</label>');
        var $input;
        if (choices) {
            $input = $('<select id="' + inputID + '"></select>');
            $.each(choices, function(index, choice) {
                var opt = '<option value="' + choice[0] + '"';
                if (choice[0] == value) {
                    opt += ' selected';
                }
                opt += '>' + choice[1] + '</option>';
                $input.append(opt);
            });
        }
        else {
            $input = $('<input type="text" id="' + inputID + '" value="' + value + '">');
        }
        $item.append($input);
        var $button = $('<a href="#" rel="' + id + '">Remove</a>').button({
                icons: {primary:'ui-icon-minus'}
        });
        $item.append($button);
        return $item;
    }

    function init(options) {
        return this.each(function() {
            var $this = $(this);
            var current_settings = {};
            $.extend(current_settings, settings, options);
            $this.data(current_settings);
            $this.append('<input type="hidden" name="' + current_settings.name + '">');
            $this.append('<div class="dictfield-items"></div>');
            $this.append('<div class="dictfield-new-item"></div>');
            $this.addClass('dictfield').addClass('ui-widget-content');
            $this.mongoDictField('update');
        });
    }

    function update(keys, items) {
        return this.each(function() {
            var $this = $(this);
            if (!keys) {
                keys = $this.data('keys');
            }

            if (!items) {
                items = $this.data('value');
            }

            var fields = $this.data('fields');
            var current_fields = fields.slice();
            var field;
            if (!current_fields.length) {
                fields = [];
                for (field in items) {
                    current_fields.push(field);
                }
            }

            var showAllFields = $this.data('showAllFields');
            var itemGenerator = $this.data('itemGenerator');
            var $items = $this.children('.dictfield-items');
            $items.empty();
            var title;
            $.each(current_fields, function(index, field) {
                if (showAllFields || (field in items)) {
                    if (!$.isEmptyObject(keys)) {
                        title = keys[field];
                    }
                    else {
                        title = field;
                    }
                    var $item = itemGenerator(field, title, items[field]);
                    $items.append($item);
                }
            });
            if ($items.length) {
                $items.show();
                $items.find('input').change(function() {
                    var id = $(this).attr('id').substr(9);
                    $this.mongoDictField('setAttr', id, $(this).val())
                });

                var $buttons = $items.find('a');
                if (!showAllFields) {
                    $buttons.click(function() {
                        var id = $(this).attr('rel');
                        $this.mongoDictField('remove', id);
                    });
                }
                else {
                    $buttons.button('disable');
                }
            }
            else {
                $items.hide();
            }

            var $newItem = $this.children('.dictfield-new-item');
            $newItem.empty();
            var newItemVisible = ($.isEmptyObject(items));
            if (!showAllFields) {
                if (fields.length) {
                    var $key_input = $('<select id="dictfield-new-item-key"></select>');
                    $.each(fields, function(index, id) {
                        if (!(id in items)) {
                            title = ($.isEmptyObject(keys)) ? id : keys[id];
                            $key_input.append("<option value=\"" + id + "\">" + title + "</option>");
                            newItemVisible = true;
                        }
                    });
                }
                else {
                    $key_input = $('<input type="text" id="dictfield-new-item-key">');
                    newItemVisible = true;
                }
            }
            if (newItemVisible) {
                $newItem.append($key_input);
                $newItem.append('<input type="text" id="dictfield-new-item-value">');
                var $addButton = $('<a href="#" rel="add">Add</a>').button({
                    icons: {primary: 'ui-icon-plus'}
                }).click(function () {
                    var key = $this.find('#dictfield-new-item-key').val();
                    var value = $this.find('#dictfield-new-item-value').val();
                    $this.mongoDictField('setAttr', key, value);
                    return false;
                });
                $newItem.append($addButton);
                $newItem.show();
            }
            else {
                $newItem.hide();
            }
            $this.children('input').val(JSON.stringify(items));
        });
    }

    function setAttr(key, value) {
        return this.each(function() {
            var $this = $(this);
            var items = $this.data('value');
            if (key) {
                items[key] = value;
            }
            $this.mongoDictField('update');
        });
    }

    function remove(key) {
        return this.each(function() {
            var $this = $(this);
            var items = $this.data('value');
            delete items[key];
            $this.mongoDictField('update');
        });
    }

    var methods = {
        'update': update,
        'setAttr': setAttr,
        'remove': remove,
        'init': init
    };

    var settings = {
        itemGenerator: createItem,
        value: {},
        fields: null,
        keys: null,
        choices: null,
        showAllFields: false
    };

    $.fn.mongoDictField = function(method) {
        // Method calling logic
        if (methods[method]) {
            return methods[method].apply(this, Array.prototype.slice.call(arguments, 1));
        }
        else if (typeof method === 'object' || ! method) {
            return methods.init.apply(this, arguments);
        }
        else {
            $.error('Method ' +  method + ' does not exist on jQuery.mongoListField');
        }

    };
})(jQuery);
