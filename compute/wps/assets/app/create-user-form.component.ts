import { Component } from '@angular/core';
import { Location } from '@angular/common';

import { User } from './user';
import { AuthService } from './auth.service';

@Component({
  templateUrl: './create-user-form.component.html',
  styleUrls: ['./forms.css']
})

export class CreateUserFormComponent {
  model: User = new User();

  constructor(
    private authService: AuthService,
    private location: Location
  ) { }

  onSubmit(): void {
    this.authService.create(this.model)
      .then(response => this.handleResponse(response));
  }

  handleResponse(response: string): void {
    this.location.go('wps/home/login');
  }
}