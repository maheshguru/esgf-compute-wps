import { Component, OnInit, Pipe, PipeTransform } from '@angular/core';

import { Header } from './pagination.component';
import { FileStat, Stats, StatsService } from './stats.service';

@Pipe({name: 'thredds'})
export class ThreddsPipe implements PipeTransform {
  transform(value: string): string {
    let thredds = value.toLowerCase().indexOf('thredds') >= 0;

    return (thredds ? `${value}.html` : value);
  }
}

@Component({
  selector: 'user-files',
  styleUrls: ['./forms.css'],
  templateUrl: './user-files.component.html', 
})
export class UserFilesComponent implements OnInit {
  stats: Promise<FileStat[]> = null;
  headers = [
    new Header('Name', 'name'), 
    new Header('Host', 'host'),
    new Header('Requested', 'requested'),
    new Header('Variable', 'variable'),
    new Header('Last Requested', 'requested_date')
  ];

  constructor(
    private statsService: StatsService
  ) { }

  ngOnInit() {
    this.stats = this.statsService.stats()
      .then(response => response.files);
  }
}
