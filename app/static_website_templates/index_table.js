$(document).ready(function () {
    // Create search input element on top of table for each column
    $('#table thead th.colSearch').each(function () {
        $(this).html('<input type="text" placeholder="Durchsuchen..." />');
    });
    // Create table
    var table = $('#table').DataTable({
        dom: 'Blprtlip',
        scrollX: true,
        pageLength: 50,
        deferRender: true,
        // Order by decreasing date (first column) after init
        order: [[0, 'desc']],
        buttons: {
            buttons: [
                {
                    extend: 'excelHtml5',
                    text: "Download as Excel",
                    autoFilter: true,
                    className: 'btn-primary btn-sm',
                }
            ],
            dom: {
                button: {
                    className: 'btn'
               },
            }
        },
        ajax: {
            url: 'items_slim.json',
            dataSrc: function(json) {
                // Update asof and version dom elements with json top level data.
                // Then pass data attribute along for datatables to display.
                document.querySelector("#asof").textContent = json.processed_asof
                document.querySelector("#version").textContent = json.version
                return json.data
            }
        },
        columns: [
            {
                data: 'date',
                width: '10%'
            },
            {
                data: 'title',
                width: '20%',
                render: function ( data, type, row, meta ) {
                  // For filter, return item_id in brackets after title.
                  // For display, return item_id in brackets after title inside an anchor tag linking to the item detail page
                  // and then append title and id of all related items as cards.
                  // For all other types, return data as is.
                  if (type === 'filter') {
                    return `${data} (${row.item_id})`;
                  } else if (type === 'display') {
                    let html = `<a href="${row.item_url}" target="_blank">${data}</a> (${row.item_id})`;
                    for (relatedItem of row.related_items) {
                      html += `
                        <div class="mt-2 shadow p-3 fw-lighter rounded" style="font-size:75%">
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-search" viewBox="0 0 16 16">
                          <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
                          </svg>
                          Möglicherweise verwandt: ${relatedItem.title} (${relatedItem.item_id}) <a class="item_id_filter" data-item-id="${relatedItem.item_id}" href="#">Anzeigen</a>
                        </div>
                      `;
                    }
                    return html;
                  } else {
                    return data;
                  }
                }
            },
            {
                data: 'category',
                width: '10%'
            },
            {
                data: 'author',
                width: '10%'
            },
            {
                data: "pdf_summary",
                width: '50%',
                render: function ( data, type, row, meta ) {
                  if (type === 'display') {
                    return `${data} <a target="_blank" href="${row.pdf_url}">(Original PDF)</a>`;
                  } else {
                    return data;
                  }
                }
            },
        ],
        // Bind search event to column search elements
        initComplete: function () {
            // Apply the search per column
            this.api()
                .columns()
                .every(function (i) {
                    var that = this;
                    $('input', `th.colSearch:eq(${i})`).on('keyup change clear', function () {
                        if (that.search() !== this.value) {
                            that.search(this.value).draw();
                        }
                    });
                });
            },
            // State management
            // Thanks to: https://stackoverflow.com/questions/55446923/datatables-1-10-using-savestate-to-remember-filtering-and-order-but-need-to-upd
            stateSave: true,
            stateSaveCallback: function (settings, data) {
                //encode current state to base64
                const state = btoa(JSON.stringify(data));
                //get query part of the url
                let searchParams = new URLSearchParams(window.location.search);
                //add encoded state into query part
                searchParams.set($(this).attr('id') + '_state', state);
                //form url with new query parameter
                const newRelativePathQuery = window.location.pathname + '?' + searchParams.toString() + window.location.hash;
                //push new url into history object, this will change the current url without need of reload
                history.pushState(null, '', newRelativePathQuery);
            },
            stateLoadParams: function(settings, data) {
              // Restore search values in column search fields
              for (i = 0; i < data.columns["length"]; i++) {
                var col_search_val = data.columns[i].search.search;
                if (col_search_val != "") {
                  $('input', `th.colSearch:eq(${i})`).val(col_search_val);
                }
              }
            },
            stateLoadCallback: function (settings) {
                const url = new URL(window.location.href);
                let state = url.searchParams.get($(this).attr('id') + '_state');
                //check the current url to see if we've got a state to restore
                if (!state) {
                    return null;
                }
                //if we got the state, decode it and add current timestamp
                state = JSON.parse(atob(state));
                state['time'] = Date.now();
                return state;
            }
        });
    // Link excel download to dedicated button
    table.buttons().container().appendTo( $('#mainHeader') );
    // Remove "dt-buttons" from container because it messes up layouting
    document.querySelector(".dt-buttons.btn-group.flex-wrap").classList.remove("dt-buttons");
    // Small manipulations to have top pagination and nr display dropdown next to each other
    document.querySelector("#table_length").classList.add("float-start");
    document.querySelector("#table_paginate").classList.add("float-end");

    // Upon clicking an id link in a table cell, filter id column with that id
    $("#table").on("click", ".item_id_filter", function(e) {
      e.preventDefault();
      e.stopPropagation();
      let el = document.querySelector('th.id_search>input');
      el.value = e.target.dataset.itemId;
      el.dispatchEvent(new Event('keyup'));
      // Highlight id search input field
      if (!el.classList.contains("pulse")) {
        el.classList.add("pulse");
        setTimeout(function() {
          el.classList.remove("pulse");
        }, 1950);
      }
    });
});
