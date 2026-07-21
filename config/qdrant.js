const { Client } = require('qdrant-client');

module.exports = {
  client: new Client({
    url: process.env.QDRANT_URL,
    apiKey: process.env.QDRANT_API_KEY,
  }),
};