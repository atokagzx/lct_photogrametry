const express = require('express');
const cors = require('cors');

require('dotenv').config();
const PORT = process.env.PORT || 3000;
const app = express();

app.use(express.static('public'));
// app.use(express.static('out2'));
app.use(express.static('../../Hack-a-ton/FGM_HACKATON/'));
// app.use(express.static('../../out2'));
app.use('/cesium', express.static(__dirname + '/node_modules/cesium/Build/Cesium'));
app.use(cors());

app.get('/', (req, res) => {
    // serve index.html
    res.sendFile(__dirname + '/index.html');
});
//  print files in the directory FGM_HACKATON
// const fs = require('fs');
// fs.readdirSync('./FGM_HACKATON').forEach(file => {
//     console.log(file);
// });

app.listen(PORT, () => console.log(`listening on port ${PORT}`));

