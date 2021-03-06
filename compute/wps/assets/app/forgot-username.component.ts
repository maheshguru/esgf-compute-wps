import { Component } from '@angular/core';

import { AuthService } from './auth.service';
import { NotificationService } from './notification.service';

@Component({
  template: `
    <div class="container">
      <form  (ngSubmit)="onSubmit()" #recoverForm="ngForm">
        <div class="form-group">
          <label for="email">Email</label>
          <input type="email" class="form-control" id="email" required [(ngModel)]="model.email" name="email">
        </div>
        <button type="submit" class="btn btn-success">Recover</button>
      </form>
    </div>
  `
})
export class ForgotUsernameComponent {
  model: any = {};

  constructor(
    private authService: AuthService,
    private notificationService: NotificationService
  ) { }

  onSubmit() {
    this.authService.forgotUsername(this.model.email)
      .then(response => {
        if (response.status === 'success') {
          this.notificationService.message(`Email with username sent to "${this.model.email}"`);

          window.location.replace(response.data.redirect);
        } else {
          this.notificationService.error(response.error);
        }
      });
  }
}
