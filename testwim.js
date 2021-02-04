window.addEventListener("load", function(){
    // Dummy Array
    var data = ["doge", "cate", "birb", "doggo", "moon moon", "awkward seal"];
  
    // Draw HTML table
    var perrow = 3, // 3 cells per row
        count = 0, // Flag for current cell
        table = document.createElement("table"),
        row = table.insertRow();
  
    for (var i of data) {
      var cell = row.insertCell();
      cell.innerHTML = i;
  
      /* You can also attach a click listener if you want
      cell.addEventListener("click", function(){
        alert("FOO!");
      });
      */
  
      // Break into next row
      count++;
      if (count%perrow==0) {
        row = table.insertRow();
      }
    }
  
    // Attach table to container
    document.getElementById("container").appendChild(table);
  });