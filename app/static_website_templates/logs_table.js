$(document).ready(function () {
    // Create search input element on top of table for each column
    $('#table thead th.colSearch').each(function () {
        $(this).html('<input type="text" placeholder="Search column" />');
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
                // Update asof dom element with asof attribute from data.json. Then
                // pass data attribute along for datatables to display.
                document.querySelector("#asof").textContent = json.processed_asof
                return json.data
            }
        },
        columns: [
            {
                data: 'status',
                width: '10%'
            },
            {
                data: 'processed_asof',
                width: '10%'
            },
            {
                data: "item_id",
                width: '10%',
                render: function ( data, type, row, meta ) {
                    if (type === "display") {
                        return `<a href="${row.item_url}" target="_blank">${data}</a>`;
                    } else {
                        return data;
                    }
                }
            },
            {
                data: "pdf_id",
                width: '10%',
                render: function ( data, type, row, meta ) {
                    if (type === "display") {
                        return `<a href="${row.pdf_url}" target="_blank">${data}</a>`;
                    } else {
                        return data;
                    }
                }
            },
            {
                data: 'error_msg',
                width: '60%'
            }
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
});
