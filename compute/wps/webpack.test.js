var webpack = require('webpack');
var helpers = require('./helpers');

module.exports = {
  devtool: 'inline-source-map',
  
  resolve: {
    extensions: ['.ts', '.js']
  },

  module: {
    rules: [
      {
        test: /\.ts$/,
        loaders: [
          {
            loader: 'awesome-typescript-loader',
            options: { configFileName: helpers.root('wps', 'assets', 'tsconfig.json') }
          }, 'angular2-template-loader'
        ]
      },
      {
        test: /\.html$/,
        loader: 'html-loader'
      },
      {
        test: /\.css$/,
        exclude: helpers.root('wps', 'assets', 'app'),
        loader: 'null-loader'
      },
      {
        test: /\.css$/,
        include: helpers.root('wps', 'assets', 'app'),
        loader: 'raw-loader'
      }
    ]
  },

  plugins: [
    new webpack.ContextReplacementPlugin(
      /angular(\\|\/)core(\\|\/)@angular/,
      helpers.root('wps', 'assets', 'app'),
      {}
    )
  ]
}
