
function initStats(container) {
    the_data = JSON.parse($("#bandcharts").attr("data-charts"))
    the_formatted_data = []
    for (i=0; i<the_data.length; i++) {
        d = the_data[i]
        the_formatted_data.push({x:Date.UTC(d[0][0],d[0][1]-1,d[0][2]), y:d[1]})
    }
    Highcharts.chart(container, {
        title: {
            text: 'Scheduled Gigs'
        },
        xAxis: {
            title: {
                text: 'Date'
            },
            type: 'datetime'
        },
        series: [{
            type: 'line',
            data: the_formatted_data,
            name: 'number of gigs'
        }],
    });

}